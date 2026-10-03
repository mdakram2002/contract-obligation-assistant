import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [contractName, setContractName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [uploadResult, setUploadResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');
    setUploadResult(null);

    try {
      const result = await api.uploadDocument(file, undefined, contractName || undefined);
      setUploadResult(result);
      setFile(null);
      setContractName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Upload Contract</h1>

      <div className="bg-white shadow rounded-lg p-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Contract Name (optional)
          </label>
          <input
            type="text"
            value={contractName}
            onChange={(e) => setContractName(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter contract name"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Contract File (PDF or DOCX)
          </label>
          <input
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.docx"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {uploadResult && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            <p className="font-semibold mb-2">Contract uploaded successfully!</p>
            <div className="text-sm space-y-1">
              <p>Contract ID: {uploadResult.contract_id}</p>
              <p>Version ID: {uploadResult.version_id}</p>
              <p>Version: {uploadResult.version_number}</p>
            </div>
            <div className="mt-3 space-x-2">
              <Link
                to="/review"
                state={{ versionId: uploadResult.version_id }}
                className="inline-block bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
              >
                Review Contract
              </Link>
              <Link
                to="/deadlines"
                state={{ versionId: uploadResult.version_id }}
                className="inline-block bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
              >
                View Deadlines
              </Link>
            </div>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload Contract'}
        </button>
      </div>
    </div>
  );
}

export default Upload;
