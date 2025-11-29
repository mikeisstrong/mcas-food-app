import React, { useState } from 'react'
import DailyDashboard from './pages/DailyDashboard'
import HistoryAccuracy from './pages/HistoryAccuracy'
import SeasonProjections from './pages/SeasonProjections'

export default function App() {
  const [activeTab, setActiveTab] = useState('daily')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Nav */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600">Grey's NBA Model</h1>
            </div>
          </div>
        </div>
      </nav>

      {/* Tab Bar */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('daily')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'daily'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Daily Dashboard
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              History & Accuracy
            </button>
            <button
              onClick={() => setActiveTab('projections')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'projections'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Season Projections
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'daily' && <DailyDashboard />}
        {activeTab === 'history' && <HistoryAccuracy />}
        {activeTab === 'projections' && <SeasonProjections />}
      </main>
    </div>
  )
}
