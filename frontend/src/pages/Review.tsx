import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { api, ExtractedItem, Obligation, Contract, ContractVersion } from '../services/api';

function Review() {
  const [versionId, setVersionId] = useState('');
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<string>('');
  const [contractVersions, setContractVersions] = useState<ContractVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [analysis, setAnalysis] = useState<any>(null);

  // Get version ID from navigation state if available
  const location = useLocation();
  useEffect(() => {
    if (location.state && (location.state as any).versionId) {
      setVersionId((location.state as any).versionId);
      handleAnalyze((location.state as any).versionId);
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
    await loadContractVersions(contractId);
  };

  const handleAnalyze = async (vid?: string) => {
    const targetVersionId = vid || versionId;
    if (!targetVersionId) {
      setError('Please select a contract version');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await api.analyzeContract(targetVersionId);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (itemId: string, itemType: 'extracted_item' | 'obligation') => {
    try {
      await api.approveItem(itemId, itemType);
      // Refresh analysis
      handleAnalyze();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleReject = async (itemId: string, itemType: 'extracted_item' | 'obligation') => {
    try {
      await api.rejectItem(itemId, itemType);
      // Refresh analysis
      handleAnalyze();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleEdit = async (
    itemId: string,
    itemType: 'extracted_item' | 'obligation',
    field: string,
    currentValue: string
  ) => {
    const updatedValue = window.prompt('Update this value:', currentValue);
    if (updatedValue === null) {
      return;
    }
    if (!updatedValue.trim()) {
      setError('Edited values cannot be empty.');
      return;
    }

    try {
      await api.editItem(itemId, itemType, { [field]: updatedValue.trim() });
      await handleAnalyze();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Edit failed');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Review Workspace</h1>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
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
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleAnalyze()}
            disabled={loading || !versionId}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Loading...' : 'Load Contract'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {analysis && (
        <div className="space-y-6">
          {analysis.ambiguities?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Unresolved Conflicts and Ambiguities</h2>
              <div className="space-y-4">
                {analysis.ambiguities.map((ambiguity: any) => (
                  <div key={ambiguity.id} className="border border-amber-200 rounded-lg p-4">
                    <div className="flex justify-between gap-4">
                      <p className="font-medium">{ambiguity.description}</p>
                      <span className="text-sm capitalize">Certainty: {ambiguity.certainty}</span>
                    </div>
                    {ambiguity.conflicting_clauses?.length > 0 && (
                      <p className="mt-2 text-sm text-gray-700">
                        Clauses: {ambiguity.conflicting_clauses.join('; ')}
                      </p>
                    )}
                    {ambiguity.notes && (
                      <p className="mt-2 text-sm text-gray-600">{ambiguity.notes}</p>
                    )}
                    {ambiguity.source_quotes?.map((quote: string, index: number) => (
                      <blockquote key={index} className="mt-2 text-sm italic text-gray-600">
                        {ambiguity.source_sections?.[index] &&
                          `Section ${ambiguity.source_sections[index]}: `}
                        "{quote}"
                      </blockquote>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.clarification_questions?.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Clarification Questions</h2>
              <div className="space-y-4">
                {analysis.clarification_questions.map((question: any) => (
                  <div key={question.id} className="border border-blue-200 rounded-lg p-4">
                    <p className="font-medium">{question.question}</p>
                    {question.context && (
                      <p className="mt-2 text-sm text-gray-600">{question.context}</p>
                    )}
                    {question.source_quotes?.map((quote: string, index: number) => (
                      <blockquote key={index} className="mt-2 text-sm italic text-gray-600">
                        {question.source_sections?.[index] &&
                          `Section ${question.source_sections[index]}: `}
                        "{quote}"
                      </blockquote>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Parties */}
          {analysis.parties && analysis.parties.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Parties</h2>
              <div className="space-y-2">
                {analysis.parties.map((party: any) => (
                  <div key={party.id} className="border rounded-lg p-3">
                    <p className="font-medium">{party.name}</p>
                    {party.role && <p className="text-sm text-gray-600">Role: {party.role}</p>}
                    {party.source_section && (
                      <p className="text-xs text-gray-500">Source: Section {party.source_section}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Items */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Extracted Items</h2>
            {analysis.extracted_items.length === 0 ? (
              <p className="text-gray-500">No items to review</p>
            ) : (
              <div className="space-y-4">
                {analysis.extracted_items.map((item: ExtractedItem) => (
                  <div key={item.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium">{item.title}</h3>
                        <p className="text-sm text-gray-600">{item.description || item.value}</p>
                        {item.source_section && (
                          <p className="text-xs text-gray-500">Section: {item.source_section}</p>
                        )}
                      </div>
                      <span className={`px-2 py-1 text-xs rounded ${
                        item.review_status === 'approved' ? 'bg-green-100 text-green-800' :
                        item.review_status === 'rejected' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {item.review_status}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                      <span>Certainty: {item.certainty}</span>
                      {item.source_page && <span>Page: {item.source_page}</span>}
                      {item.is_stale === 'true' && (
                        <span className="font-semibold text-amber-700">Potentially stale</span>
                      )}
                    </div>
                    {item.source_quote && (
                      <p className="text-sm text-gray-500 italic mt-2">"{item.source_quote}"</p>
                    )}
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => handleEdit(
                          item.id,
                          'extracted_item',
                          item.description ? 'description' : 'value',
                          item.description || item.value || ''
                        )}
                        className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700"
                      >
                        Edit
                      </button>
                      {item.review_status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(item.id, 'extracted_item')}
                            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleReject(item.id, 'extracted_item')}
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Obligations */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Obligations</h2>
            {analysis.obligations.length === 0 ? (
              <p className="text-gray-500">No obligations to review</p>
            ) : (
              <div className="space-y-4">
                {analysis.obligations.map((obligation: Obligation) => (
                  <div key={obligation.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium">{obligation.description}</h3>
                        {obligation.responsible_party && (
                          <p className="text-sm text-gray-600">Responsible: {obligation.responsible_party}</p>
                        )}
                        {obligation.deadline && (
                          <p className="text-sm text-gray-600">Deadline: {new Date(obligation.deadline).toLocaleDateString()}</p>
                        )}
                        {obligation.source_section && (
                          <p className="text-xs text-gray-500">Section: {obligation.source_section}</p>
                        )}
                      </div>
                      <span className={`px-2 py-1 text-xs rounded ${
                        obligation.review_status === 'approved' ? 'bg-green-100 text-green-800' :
                        obligation.review_status === 'rejected' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {obligation.review_status}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                      <span>Certainty: {obligation.certainty}</span>
                      {obligation.source_page && <span>Page: {obligation.source_page}</span>}
                      {obligation.is_stale === 'true' && (
                        <span className="font-semibold text-amber-700">Potentially stale</span>
                      )}
                    </div>
                    {obligation.source_quote && (
                      <p className="text-sm text-gray-500 italic mt-2">"{obligation.source_quote}"</p>
                    )}
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => handleEdit(
                          obligation.id,
                          'obligation',
                          'description',
                          obligation.description
                        )}
                        className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700"
                      >
                        Edit
                      </button>
                      {obligation.review_status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(obligation.id, 'obligation')}
                            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleReject(obligation.id, 'obligation')}
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Review;
