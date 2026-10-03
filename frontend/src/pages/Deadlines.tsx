import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { api, Deadline, Contract, ContractVersion } from '../services/api';

function Deadlines() {
  const [versionId, setVersionId] = useState('');
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<string>('');
  const [contractVersions, setContractVersions] = useState<ContractVersion[]>([]);
  const [daysAhead, setDaysAhead] = useState('180');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);

  const location = useLocation();
  useEffect(() => {
    if (location.state && (location.state as any).versionId) {
      setVersionId((location.state as any).versionId);
      handleCalculate((location.state as any).versionId);
    }
  }, [location]);

  useEffect(() => {
    loadContracts();
  }, []);

  const loadContracts = async () => {
    try {
      const result = await api.getContracts();
      setContracts(result.contracts);
    } catch (err) {
      console.error('Failed to load contracts:', err);
    }
  };

  const loadContractVersions = async (contractId: string) => {
    try {
      const result = await api.getContractVersions(contractId);
      setContractVersions(result.versions);
    } catch (err) {
      console.error('Failed to load versions:', err);
    }
  };

  const handleContractChange = async (contractId: string) => {
    setSelectedContract(contractId);
    setVersionId('');
    setDeadlines([]);
    setError('');
    await loadContractVersions(contractId);
  };

  const handleCalculate = async (vid?: string) => {
    const targetVersionId = vid || versionId;
    if (!targetVersionId) {
      setError('Please select a contract version');
      return;
    }

    const dayCount = Number(daysAhead);
    if (!Number.isInteger(dayCount) || dayCount < 1 || dayCount > 365) {
      setError('Days ahead must be a whole number between 1 and 365.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await api.calculateDeadlines(
        targetVersionId,
        dayCount,
        selectedContract || undefined
      );
      setDeadlines(result.deadlines);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Upcoming Deadlines</h1>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Contract
            </label>
            <select
              value={selectedContract}
              onChange={(e) => handleContractChange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Select a contract --</option>
              {contracts.map((contract) => (
                <option key={contract.id} value={contract.id}>
                  {contract.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Version
            </label>
            <select
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              disabled={!selectedContract}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            >
              <option value="">-- Select a version --</option>
              {contractVersions.map((version) => (
                <option key={version.id} value={version.id}>
                  Version {version.version_number} - {version.file_name || 'Pasted Text'}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Days Ahead (1-365)
            </label>
            <input
              type="number"
              value={daysAhead}
              onChange={(e) => {
                setDaysAhead(e.target.value);
                setError('');
              }}
              min="1"
              max="365"
              step="1"
              aria-invalid={!!error && (
                !Number.isInteger(Number(daysAhead)) ||
                Number(daysAhead) < 1 ||
                Number(daysAhead) > 365
              )}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        <button
          onClick={() => handleCalculate()}
          disabled={loading || !versionId}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Calculating...' : 'Calculate Deadlines'}
        </button>
      </div>

      {error && (
        <div role="alert" aria-live="assertive" className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {deadlines.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Deadline
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Days Remaining
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Certainty
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {deadlines.map((deadline) => (
                <tr key={deadline.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {deadline.description}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                    {deadline.type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(deadline.deadline).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 text-xs rounded ${
                      deadline.days_remaining <= 7 ? 'bg-red-100 text-red-800' :
                      deadline.days_remaining <= 30 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {deadline.days_remaining} days
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                    {deadline.certainty}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deadlines.length === 0 && !loading && versionId && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No upcoming deadlines</h3>
          <p className="mt-1 text-sm text-gray-500">
            No deadlines found within the selected time period.
          </p>
        </div>
      )}

      {!versionId && !loading && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Select a contract version</h3>
          <p className="mt-1 text-sm text-gray-500">
            Choose a contract and version to view upcoming deadlines.
          </p>
        </div>
      )}
    </div>
  );
}

export default Deadlines;
