import React, { useState, useEffect } from 'react';
import { fetchSeasonProjections } from '../utils/api';

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

const SeasonProjections = () => {
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
  const [projections, setProjections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('projected_total_wins');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    loadProjections();
  }, []);

  const loadProjections = async () => {
    setLoading(true);
    setError(null);
    try {
      // Always loads current season (2025-26) with blended model
      const data = await fetchSeasonProjections();
      setProjections(data.projections || []);
    } catch (err) {
      setError(err.message || 'Failed to load projections');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const sortedProjections = [...projections].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];

    if (typeof aVal === 'string') {
      return sortOrder === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return sortOrder === 'asc'
      ? aVal - bVal
      : bVal - aVal;
  });

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null;
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
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
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow p-6 text-white">
        <h2 className="text-2xl font-bold">2025-26 Season Projections</h2>
        <p className="text-blue-100 mt-2">Based on blended model (70% LightGBM + 30% ELO)</p>
        <p className="text-xs text-blue-200 mt-2">Methodology: Probability Summation + Monte Carlo Simulation (10,000 iterations with dynamic team rating updates)</p>
      </div>

      {/* Stats Summary */}
      {projections.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm font-medium">Total Teams</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {projections.filter(p => p.remaining_games > 0).length}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm font-medium">Avg Remaining Games</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {(projections.reduce((sum, p) => sum + p.remaining_games, 0) / projections.filter(p => p.remaining_games > 0).length).toFixed(1)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm font-medium">Highest Proj Wins</div>
            <div className="text-3xl font-bold text-green-600 mt-1">
              {Math.max(...projections.map(p => p.projected_total_wins)).toFixed(1)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm font-medium">Lowest Proj Wins</div>
            <div className="text-3xl font-bold text-red-600 mt-1">
              {Math.min(...projections.filter(p => p.remaining_games > 0).map(p => p.projected_total_wins)).toFixed(1)}
            </div>
          </div>
        </div>
      )}

      {/* Projections Table */}
      {projections.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Team Projections</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    onClick={() => handleSort('team_name')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Team {<SortIcon column="team_name" />}
                  </th>
                  <th
                    onClick={() => handleSort('current_wins')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Current Record {<SortIcon column="current_wins" />}
                  </th>
                  <th
                    onClick={() => handleSort('remaining_games')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Remaining {<SortIcon column="remaining_games" />}
                  </th>
                  <th
                    onClick={() => handleSort('projected_remaining_wins')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Proj Rem Wins {<SortIcon column="projected_remaining_wins" />}
                  </th>
                  <th
                    onClick={() => handleSort('projected_total_wins')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Prob Sum Final {<SortIcon column="projected_total_wins" />}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Monte Carlo (90% CI)
                  </th>
                  <th
                    onClick={() => handleSort('projected_win_pct')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Win % {<SortIcon column="projected_win_pct" />}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedProjections.filter(p => p.remaining_games > 0).map((proj) => (
                    <tr key={proj.team_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <TeamLogo abbr={proj.team_abbr} />
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {proj.team_abbr}
                            </div>
                            <div className="text-xs text-gray-500">{proj.team_name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {proj.current_wins}-{proj.current_losses}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {proj.remaining_games}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {proj.projected_remaining_wins.toFixed(1)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {proj.projected_total_wins}-{proj.projected_total_losses}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {proj.monte_carlo ? (
                          <div className="space-y-1">
                            <div className="font-semibold text-blue-600">{proj.monte_carlo.mean_wins}</div>
                            <div className="text-xs text-gray-500">
                              {proj.monte_carlo.percentile_10}-{proj.monte_carlo.percentile_90}
                            </div>
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {(proj.projected_win_pct * 100).toFixed(1)}%
                      </td>
                    </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {projections.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No projections found.</p>
        </div>
      )}
    </div>
  );
};

export default SeasonProjections;
