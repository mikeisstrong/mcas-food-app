export const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export const formatPercent = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return `${(value * 100).toFixed(1)}%`
}

export const formatSpread = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}`
}

export const getConfidenceColor = (prob) => {
  if (prob === null || prob === undefined) return 'gray'
  if (prob >= 0.65) return 'green'
  if (prob >= 0.55) return 'yellow'
  return 'red'
}

export const getConfidenceBucket = (prob) => {
  if (prob === null || prob === undefined) return 'Unknown'
  if (prob >= 0.65) return 'High'
  if (prob >= 0.55) return 'Medium'
  return 'Low'
}

export const getConfidenceBgColor = (bucket) => {
  switch (bucket) {
    case 'High':
      return 'bg-green-100 text-green-800'
    case 'Medium':
      return 'bg-yellow-100 text-yellow-800'
    case 'Low':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}
