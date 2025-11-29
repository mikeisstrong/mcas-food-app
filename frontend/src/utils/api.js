const API_BASE = '/api'

export const fetchDailyReport = async (queryDate = null) => {
  const url = queryDate
    ? `${API_BASE}/report/daily?query_date=${queryDate}`
    : `${API_BASE}/report/daily`

  const response = await fetch(url)
  if (!response.ok) throw new Error('Failed to fetch daily report')
  return await response.json()
}

export const fetchGames = async (options = {}) => {
  const params = new URLSearchParams()
  if (options.start_date) params.append('start_date', options.start_date)
  if (options.startDate) params.append('start_date', options.startDate)
  if (options.end_date) params.append('end_date', options.end_date)
  if (options.endDate) params.append('end_date', options.endDate)
  if (options.team) params.append('team', options.team)
  if (options.confidence) params.append('confidence', options.confidence)
  params.append('skip', options.skip || 0)
  params.append('limit', options.limit || 50)

  const url = `${API_BASE}/games?${params}`
  const response = await fetch(url)
  if (!response.ok) throw new Error('Failed to fetch games')
  return await response.json()
}

export const fetchMetricsSummary = async (options = {}) => {
  const params = new URLSearchParams()
  if (options.start_date) params.append('start_date', options.start_date)
  if (options.startDate) params.append('start_date', options.startDate)
  if (options.end_date) params.append('end_date', options.end_date)
  if (options.endDate) params.append('end_date', options.endDate)

  const url = `${API_BASE}/metrics/summary?${params}`
  const response = await fetch(url)
  if (!response.ok) throw new Error('Failed to fetch metrics summary')
  return await response.json()
}

export const fetchSeasonProjections = async (season = 2025, basis = 'blend') => {
  const url = `${API_BASE}/projections/season?season=${season}&basis=${basis}`
  const response = await fetch(url)
  if (!response.ok) throw new Error('Failed to fetch projections')
  return await response.json()
}
