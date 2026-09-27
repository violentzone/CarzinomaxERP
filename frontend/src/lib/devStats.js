import { num, parseDate } from './format'

/**
 * Derive per-project traction from the flat investment and download lists.
 *
 * Downloads are point-in-time snapshots per platform, so "downloads" for a
 * project is the sum of the *latest* snapshot on each platform (not the sum of
 * every row), and "stars" is the highest star count seen in those snapshots.
 *
 * @returns {Record<string, {spend, downloads, stars, platforms, lastDate, investmentCount, snapshotCount}>}
 */
export function projectStats(projects = [], investments = [], downloads = []) {
  const stats = {}
  const ensure = (pid) => {
    const k = String(pid)
    if (!stats[k]) {
      stats[k] = {
        spend: 0,
        downloads: 0,
        stars: 0,
        platforms: [],
        lastDate: null,
        investmentCount: 0,
        snapshotCount: 0,
      }
    }
    return stats[k]
  }
  const bump = (s, d) => {
    const dt = parseDate(d)
    if (dt && (!s.lastDate || dt > s.lastDate)) s.lastDate = dt
  }

  for (const p of projects) ensure(p.project_id)

  for (const inv of investments) {
    const s = ensure(inv.project_id)
    s.spend += num(inv.amount)
    s.investmentCount += 1
    bump(s, inv.date)
  }

  // latest snapshot per (project, platform)
  const latest = {}
  for (const dl of downloads) {
    const key = `${dl.project_id}::${dl.platform}`
    const cur = latest[key]
    if (!cur || (parseDate(dl.date) ?? 0) > (parseDate(cur.date) ?? 0)) latest[key] = dl
    const s = ensure(dl.project_id)
    s.snapshotCount += 1
    bump(s, dl.date)
  }
  for (const dl of Object.values(latest)) {
    const s = ensure(dl.project_id)
    s.downloads += num(dl.download_count)
    s.stars = Math.max(s.stars, num(dl.star_count))
    s.platforms.push(dl.platform)
  }
  return stats
}

/** Download totals per calendar day across projects — for a trend chart. */
export function downloadSeries(downloads = [], { projectId = null } = {}) {
  const byDate = {}
  for (const dl of downloads) {
    if (projectId && String(dl.project_id) !== String(projectId)) continue
    const k = dl.date
    byDate[k] = byDate[k] || { date: k, downloads: 0, stars: 0 }
    byDate[k].downloads += num(dl.download_count)
    byDate[k].stars = Math.max(byDate[k].stars, num(dl.star_count))
  }
  return Object.values(byDate).sort((a, b) => (parseDate(a.date) ?? 0) - (parseDate(b.date) ?? 0))
}
