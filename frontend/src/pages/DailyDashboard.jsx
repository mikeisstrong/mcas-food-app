import React, { useState, useEffect } from 'react';
import { fetchDailyReport } from '../utils/api';
import { formatDate, formatPercent, formatSpread, getConfidenceColor, getConfidenceBgColor } from '../utils/formatters';

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

const DailyDashboard = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchDailyReport(selectedDate);
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to load daily report');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() - 1);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  const handleNextDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + 1);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  const handleToday = () => {
    setSelectedDate(new Date().toISOString().split('T')[0]);
  };

  const getAccuracyBadge = (accuracy) => {
    if (accuracy >= 0.60) return { bg: 'bg-green-50', text: 'text-green-700', label: 'Above Average' };
    if (accuracy >= 0.50) return { bg: 'bg-gray-50', text: 'text-gray-700', label: 'Average' };
    return { bg: 'bg-red-50', text: 'text-red-700', label: 'Below Average' };
  };

  const getErrorColor = (error) => {
    if (error <= 10) return 'bg-green-50 text-green-700';
    if (error <= 20) return 'bg-yellow-50 text-yellow-700';
    return 'bg-red-50 text-red-700';
  };

  const getCorrectPill = (game) => {
    if (game.correct === true) {
      return <span className="inline-flex px-3 py-1 bg-green-100 text-green-800 text-sm font-semibold rounded-full">✓ Yes</span>;
    }
    if (game.correct === false) {
      return <span className="inline-flex px-3 py-1 bg-red-100 text-red-800 text-sm font-semibold rounded-full">✗ No</span>;
    }
    return <span className="inline-flex px-3 py-1 bg-blue-100 text-blue-800 text-sm font-semibold rounded-full">Pending</span>;
  };

  const TeamLogo = ({ abbr }) => {
    const [imageError, setImageError] = useState(false);
    const logoUrl = NBA_TEAM_LOGOS[abbr];

    if (!logoUrl || imageError) {
      return (
        <div className="w-7 h-7 rounded-full bg-gray-300 flex items-center justify-center text-xs font-bold text-gray-700">
          {abbr}
        </div>
      );
    }

    return (
      <img
        src={logoUrl}
        alt={abbr}
        className="w-7 h-7 object-contain"
        onError={() => setImageError(true)}
      />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-600">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-600">Error: {error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const yesterdayGames = data.yesterday?.games || [];
  const todayGames = data.today?.games || [];
  const summaryMetrics = data.summary_metrics || {};

  console.log('=== DASHBOARD RENDER ===');
  console.log('Full data:', data);
  console.log('todayGames:', todayGames);
  console.log('todayGames length:', todayGames.length);
  console.log('todayGames.length > 0?', todayGames.length > 0);
  console.log('Condition result:', todayGames && todayGames.length > 0);

  // Get team calculated metrics from game stats
  const getTeamMetrics = (game, teamAbbr, isHome) => {
    if (!game) return null;

    // Get the team stats from the game (home or away)
    const stats = isHome ? game.home_team_stats : game.away_team_stats;
    if (!stats) return null;

    return {
      ppf: stats.points_for?.toFixed(1) || '—',
      ppa: stats.points_against?.toFixed(1) || '—',
      pointDiff: stats.point_differential?.toFixed(1) || '—',
      elo: stats.elo_rating?.toFixed(0) || '—',
      daysRest: stats.days_rest || '—',
      backToBack: stats.back_to_back ? 'Yes' : 'No'
    };
  };

  // Get team-specific metrics for display
  const getTeamPrediction = (game, teamAbbr) => {
    const isHome = game.home_team_abbr === teamAbbr;
    const winPct = isHome ? game.pred_home_win_pct : (1 - game.pred_home_win_pct);
    const spread = isHome ? game.pred_spread : -game.pred_spread;
    return { winPct, spread };
  };

  const yesterdayGamesCompleted = yesterdayGames.length > 0 && yesterdayGames.some(g => (g.home_score != null && g.away_score != null) && (g.home_score !== 0 || g.away_score !== 0));

  const formatDateDisplay = (dateStr) => {
    // Parse as UTC to avoid timezone offset issues
    const [year, month, day] = dateStr.split('-');
    const date = new Date(Date.UTC(parseInt(year), parseInt(month) - 1, parseInt(day)));
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Calculate additional metrics
  const yesterdayAccuracy = summaryMetrics.yesterday_accuracy || 0;
  const accuracyBadge = getAccuracyBadge(yesterdayAccuracy);
  const highConfidenceAccuracy = summaryMetrics.high_confidence_accuracy || 0;
  const avgError = summaryMetrics.avg_error || 0;

  // Render team row (reusable for both yesterday and today)
  const TeamRow = ({ game, teamAbbr, isHome, showResult = false }) => {
    const isAway = !isHome;
    const score = isHome ? game.home_score : game.away_score;
    const prediction = getTeamPrediction(game, teamAbbr);
    const metrics = getTeamMetrics(game, teamAbbr, isHome);
    const hasScore = score != null;
    const gameCompleted = game.home_score != null && game.away_score != null;

    return (
      <div className={`px-6 py-4 ${isHome ? 'bg-gray-200 hover:bg-gray-300' : 'bg-white hover:bg-gray-50 border-b border-gray-200'} transition-colors`}>
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="w-8">
            <TeamLogo abbr={teamAbbr} />
          </div>

          {/* Team Abbr */}
          <div className="w-16">
            <div className="text-sm font-semibold text-gray-900">{teamAbbr}</div>
          </div>

          {/* Score */}
          <div className="w-12 text-center">
            <div className={`text-base font-bold ${hasScore ? 'text-gray-900' : 'text-gray-500'}`}>
              {hasScore ? score : '—'}
            </div>
          </div>

          {/* Win % */}
          <div className="w-16 text-center">
            <div className={`text-sm font-semibold ${prediction.winPct >= 0.5 ? 'text-blue-600' : 'text-gray-600'}`}>
              {formatPercent(prediction.winPct)}
            </div>
          </div>

          {/* Margin/Spread */}
          <div className="w-16 text-center">
            <div className="text-sm font-semibold text-gray-900">
              {formatSpread(prediction.spread)}
            </div>
          </div>

          {/* Metrics (PPF, PPA, Diff, ELO, Rest) */}
          {metrics ? (
            <>
              <div className="w-16 text-center"><div className="text-sm font-semibold text-gray-900">{metrics.ppf}</div></div>
              <div className="w-16 text-center"><div className="text-sm font-semibold text-gray-900">{metrics.ppa}</div></div>
              <div className="w-16 text-center"><div className="text-sm font-semibold text-gray-900">{metrics.pointDiff}</div></div>
              <div className="w-14 text-center"><div className="text-sm font-semibold text-gray-900">{metrics.elo}</div></div>
              <div className="w-12 text-center"><div className="text-sm font-semibold text-gray-900">{metrics.daysRest}d</div></div>
            </>
          ) : (
            <>
              <div className="w-16 text-center"><div className="text-sm text-gray-400">—</div></div>
              <div className="w-16 text-center"><div className="text-sm text-gray-400">—</div></div>
              <div className="w-16 text-center"><div className="text-sm text-gray-400">—</div></div>
              <div className="w-14 text-center"><div className="text-sm text-gray-400">—</div></div>
              <div className="w-12 text-center"><div className="text-sm text-gray-400">—</div></div>
            </>
          )}

          {/* Result and Error (only for completed games) */}
          {showResult && gameCompleted && (
            <>
              <div className="w-20 text-center">
                {prediction.winPct >= 0.5 && (
                  isHome ? (
                    game.home_score > game.away_score ? (
                      <span className="text-sm font-semibold text-green-600">✓</span>
                    ) : (
                      <span className="text-sm font-semibold text-red-600">✗</span>
                    )
                  ) : (
                    game.away_score > game.home_score ? (
                      <span className="text-sm font-semibold text-green-600">✓</span>
                    ) : (
                      <span className="text-sm font-semibold text-red-600">✗</span>
                    )
                  )
                )}
              </div>
              <div className="w-16 text-center">
                <div className={`text-sm font-semibold ${game.error <= 10 ? 'text-green-600' : game.error <= 20 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {game.error != null ? formatSpread(game.error) : '—'}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Date Selector Header */}
      <div className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={handlePrevDay}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Previous day"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900">{formatDateDisplay(selectedDate)}</h1>
                <button
                  onClick={handleToday}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Today
                </button>
              </div>
              <button
                onClick={handleNextDay}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Next day"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Row 1: Primary KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Yesterday Accuracy */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-1">Yesterday Accuracy</p>
                <p className="text-5xl font-bold text-gray-900">{formatPercent(yesterdayAccuracy)}</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-1 rounded ${accuracyBadge.bg} ${accuracyBadge.text}`}>
                {accuracyBadge.label}
              </span>
            </div>
            <p className="text-sm text-gray-600">{yesterdayGames.length} games analyzed</p>
          </div>

          {/* High Confidence Accuracy */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <div>
              <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-1">High Confidence Accuracy</p>
              <p className="text-5xl font-bold text-gray-900">{formatPercent(highConfidenceAccuracy)}</p>
            </div>
            <p className="text-sm text-gray-600 mt-4">Games ≥65% probability</p>
          </div>

          {/* Games Played */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <div>
              <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-1">Games Yesterday</p>
              <p className="text-5xl font-bold text-gray-900">{yesterdayGames.length}</p>
            </div>
            <p className="text-sm text-gray-600 mt-4">Predictions analyzed</p>
          </div>
        </div>

        {/* Row 2: Secondary KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Avg Spread Error */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-3">Avg Spread Error</p>
            <p className={`text-3xl font-bold ${avgError <= 10 ? 'text-green-600' : avgError <= 20 ? 'text-yellow-600' : 'text-red-600'}`}>
              {formatSpread(avgError)}
            </p>
            <p className="text-sm text-gray-600 mt-2">points off</p>
          </div>

          {/* Season Accuracy (placeholder) */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-3">Season Accuracy</p>
            <p className="text-3xl font-bold text-gray-900">—</p>
            <p className="text-sm text-gray-600 mt-2">To date</p>
          </div>

          {/* Calibration Score (placeholder) */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-3">Calibration</p>
            <p className="text-3xl font-bold text-gray-900">—</p>
            <p className="text-sm text-gray-600 mt-2">Probability accuracy</p>
          </div>

          {/* Underdog Hit Rate (placeholder) */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <p className="text-xs uppercase tracking-wider text-gray-600 font-semibold mb-3">Underdog Hit Rate</p>
            <p className="text-3xl font-bold text-gray-900">—</p>
            <p className="text-sm text-gray-600 mt-2">Yesterday</p>
          </div>
        </div>

        {/* Last Night's Results Section */}
        {yesterdayGames && yesterdayGames.length > 0 && yesterdayGamesCompleted && (
          <div className="mb-12">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Last Night's Results</h2>
              <p className="text-sm text-gray-600 mt-2">Detailed breakdown by team with predictions and outcomes</p>
            </div>

            {/* Column Headers */}
            <div className="bg-gray-100 rounded-t-lg border border-gray-300 border-b-0 px-6 py-4">
              <div className="flex items-center gap-4 text-xs uppercase tracking-widest font-semibold text-gray-700">
                <div className="w-8"></div>
                <div className="w-16">Team</div>
                <div className="w-12 text-center">Score</div>
                <div className="w-16 text-center">Win %</div>
                <div className="w-16 text-center">Margin</div>
                <div className="w-16 text-center">PPF</div>
                <div className="w-16 text-center">PPA</div>
                <div className="w-16 text-center">Diff</div>
                <div className="w-14 text-center">ELO</div>
                <div className="w-12 text-center">Rest</div>
                <div className="w-20 text-center">Result</div>
                <div className="w-16 text-center">Error</div>
              </div>
            </div>

            <div className="bg-transparent rounded-b-lg overflow-hidden">
              {yesterdayGames.map((game, gameIndex) => (
                <div key={gameIndex} className="border border-gray-300 rounded-lg overflow-hidden mb-4 last:mb-0">
                  <TeamRow game={game} teamAbbr={game.away_team_abbr} isHome={false} showResult={true} />
                  <TeamRow game={game} teamAbbr={game.home_team_abbr} isHome={true} showResult={true} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Today's Schedule Section */}
        {todayGames && todayGames.length > 0 && (
          <div className="mb-12">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Today's Schedule & Projections</h2>
              <p className="text-sm text-gray-600 mt-2">Upcoming games with model predictions and team metrics</p>
            </div>

            {/* Column Headers (no Result/Error columns for upcoming games) */}
            <div className="bg-gray-100 rounded-t-lg border border-gray-300 border-b-0 px-6 py-4">
              <div className="flex items-center gap-4 text-xs uppercase tracking-widest font-semibold text-gray-700">
                <div className="w-8"></div>
                <div className="w-16">Team</div>
                <div className="w-12 text-center">Score</div>
                <div className="w-16 text-center">Win %</div>
                <div className="w-16 text-center">Margin</div>
                <div className="w-16 text-center">PPF</div>
                <div className="w-16 text-center">PPA</div>
                <div className="w-16 text-center">Diff</div>
                <div className="w-14 text-center">ELO</div>
                <div className="w-12 text-center">Rest</div>
              </div>
            </div>

            <div className="bg-transparent rounded-b-lg overflow-hidden">
              {todayGames.map((game, gameIndex) => (
                <div key={gameIndex} className="border border-gray-300 rounded-lg overflow-hidden mb-4 last:mb-0">
                  <TeamRow game={game} teamAbbr={game.away_team_abbr} isHome={false} showResult={false} />
                  <TeamRow game={game} teamAbbr={game.home_team_abbr} isHome={true} showResult={false} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Games Message */}
        {(!yesterdayGames || yesterdayGames.length === 0) && (!todayGames || todayGames.length === 0) && (
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
            <p className="text-gray-600">No games found for this date.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DailyDashboard;
