import React, { useState, useEffect } from 'react';
import { fetchGames, fetchMetricsSummary } from '../utils/api';
import { formatDate, formatPercent, formatSpread, getConfidenceBgColor, getConfidenceBucket } from '../utils/formatters';

const NBA_TEAM_LOGOS = {
  ATL: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/atl.png',
  BOS: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/bos.png',
  BRK: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/bkn.png',
  BKN: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/bkn.png',
  CHA: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/cha.png',
  CHI: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/chi.png',
  CLE: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/cle.png',
  DAL: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/dal.png',
  DEN: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/den.png',
  DET: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/det.png',
  GSW: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/gsw.png',
  HOU: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/hou.png',
  LAC: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/lac.png',
  LAL: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/lal.png',
  MEM: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mem.png',
  MIA: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mia.png',
  MIL: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/mil.png',
  MIN: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/min.png',
  NOP: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/no.png',
  NYK: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/ny.png',
  OKC: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/okc.png',
  ORL: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/orl.png',
  PHI: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/phi.png',
  PHX: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/phx.png',
  POR: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/por.png',
  SAC: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/sac.png',
  SAS: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/sa.png',
  TOR: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/tor.png',
  UTA: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/utah.png',
  VAN: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/van.png',
  WAS: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/wsh.png',
  IND: 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/ind.png',
};

const HistoryAccuracy = () => {
  const TeamLogo = ({ abbr }) => {
    const [imageError, setImageError] = useState(false);
    const logoUrl = NBA_TEAM_LOGOS[abbr];

    if (!logoUrl || imageError) {
      return (
        <div className="w-6 h-6 rounded-full bg-gray-300 flex items-center justify-center text-xs font-bold text-gray-700">
          {abbr}
        </div>
      );
    }

    return (
      <img
        src={logoUrl}
        alt={abbr}
        className="w-6 h-6 object-contain"
        onError={() => setImageError(true)}
      />
    );
  };
  const [filters, setFilters] = useState({
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
  });
  const [games, setGames] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [gamesData, metricsData] = await Promise.all([
        fetchGames({
          start_date: filters.startDate,
          end_date: filters.endDate,
          skip: 0,
          limit: 500
        }),
        fetchMetricsSummary({
          start_date: filters.startDate,
          end_date: filters.endDate
        })
      ]);
      setGames(gamesData.games || []);
      setMetrics(metricsData);
    } catch (err) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handlePreset = (days) => {
    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    setFilters(prev => ({ ...prev, startDate, endDate }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handlePreset(7)}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition text-sm font-medium"
          >
            Last 7 Days
          </button>
          <button
            onClick={() => handlePreset(30)}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition text-sm font-medium"
          >
            Last 30 Days
          </button>
          <button
            onClick={() => handlePreset(180)}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition text-sm font-medium"
          >
            Last 6 Months
          </button>
        </div>
      </div>

      {/* Summary Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase">Overall Accuracy</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{formatPercent(metrics.overall_accuracy)}</p>
            <p className="text-sm text-gray-600 mt-1">{metrics.total_games} games</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase">Mean Absolute Error</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{metrics.spread_error?.mean_absolute_error?.toFixed(2) || 'N/A'}</p>
            <p className="text-sm text-gray-600 mt-1">Points off</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase">Within 5 Points</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{formatPercent(metrics.spread_error?.within_5_points)}</p>
            <p className="text-sm text-gray-600 mt-1">Spread accuracy</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase">Within 10 Points</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{formatPercent(metrics.spread_error?.within_10_points)}</p>
            <p className="text-sm text-gray-600 mt-1">Spread accuracy</p>
          </div>
        </div>
      )}

      {/* By Confidence Breakdown */}
      {metrics?.by_confidence && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Accuracy by Confidence</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(metrics.by_confidence).map(([level, data]) => (
              <div key={level} className={`p-4 rounded-lg ${getConfidenceBgColor(level)}`}>
                <h4 className="font-medium mb-2">{level} Confidence</h4>
                <p className="text-2xl font-bold mb-1">{formatPercent(data.pct)}</p>
                <p className="text-sm">{data.correct} of {data.total} correct</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Games Table */}
      {games.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Games ({games.length})</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Matchup</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pred %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pred Diff</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Final Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Correct?</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {games.map((game, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatDate(game.date)}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <TeamLogo abbr={game.away_team_abbr} />
                          <span className="text-xs font-semibold text-gray-700">{game.away_team_abbr}</span>
                        </div>
                        <span className="text-xs text-gray-400">@</span>
                        <div className="flex items-center gap-1">
                          <TeamLogo abbr={game.home_team_abbr} />
                          <span className="text-xs font-semibold text-gray-700">{game.home_team_abbr}</span>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {game.away_team} @ {game.home_team}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded ${getConfidenceBgColor(getConfidenceBucket(game.pred_home_win_pct))}`}>
                        {formatPercent(game.pred_home_win_pct)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatSpread(game.pred_spread)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {game.home_score != null && game.away_score != null
                        ? `${game.away_score} - ${game.home_score}`
                        : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {game.correct != null && (
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded ${
                          game.correct
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {game.correct ? 'Yes' : 'No'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {game.error != null ? formatSpread(game.error) : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {games.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No games found for this date range.</p>
        </div>
      )}
    </div>
  );
};

export default HistoryAccuracy;
