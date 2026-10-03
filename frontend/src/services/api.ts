const API_BASE = '/api';

async function getErrorMessage(response: Response): Promise<string> {
  const body = await response.text();
  if (!body) {
    return `HTTP error! status: ${response.status}`;
  }

  try {
    const payload: unknown = JSON.parse(body);
    if (
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload
    ) {
      const detail = payload.detail;
      if (typeof detail === 'string') {
        return detail;
      }
      if (Array.isArray(detail)) {
        const daysAheadValidation = detail.some(
          (issue) =>
            typeof issue === 'object' &&
            issue !== null &&
            'loc' in issue &&
            Array.isArray(issue.loc) &&
            issue.loc.includes('days_ahead')
        );
        if (daysAheadValidation) {
          return 'Days ahead must be a whole number between 1 and 365.';
        }
        return detail
          .map((issue) =>
            typeof issue === 'object' &&
            issue !== null &&
            'msg' in issue &&
            typeof issue.msg === 'string'
              ? issue.msg
              : ''
          )
          .filter(Boolean)
          .join(' ');
      }
    }
  } catch {
    return body;
  }

  return body;
}

export interface Contract {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ContractVersion {
  id: string;
  contract_id: string;
  version_number: number;
  file_name?: string;
  file_type?: string;
  created_at: string;
}

export interface Party {
  id: string;
  name: string;
  role?: string;
  source_section?: string;
  source_page?: number;
  source_quote?: string;
}

export interface ExtractedItem {
  id: string;
  item_type: string;
  title: string;
  value?: string;
  date_value?: string;
  notice_period_days?: number;
  description?: string;
  conditions?: string;
  purpose?: string;
  automatic?: string;
  certainty: string;
  source_section?: string;
  source_page?: number;
  source_quote?: string;
  notes?: string;
  review_status: string;
  is_stale: string;
  user_edited: string;
  created_at: string;
  updated_at: string;
}

export interface Obligation {
  id: string;
  description: string;
  responsible_party?: string;
  deadline?: string;
  deadline_description?: string;
  certainty: string;
  source_section?: string;
  source_page?: number;
  source_quote?: string;
  notes?: string;
  review_status: string;
  is_stale: string;
  user_edited: string;
  created_at: string;
  updated_at: string;
}

export interface Ambiguity {
  id: string;
  description: string;
  conflicting_clauses?: string[];
  certainty: string;
  source_sections?: string[];
  source_pages?: number[];
  source_quotes?: string[];
  notes?: string;
  resolved: string;
  created_at: string;
}

export interface ClarificationQuestion {
  id: string;
  question: string;
  related_clauses?: string[];
  context?: string;
  source_sections?: string[];
  source_pages?: number[];
  source_quotes?: string[];
  answered: string;
  answer?: string;
  created_at: string;
}

export interface Analysis {
  contract_version_id: string;
  parties: Party[];
  extracted_items: ExtractedItem[];
  obligations: Obligation[];
  ambiguities: Ambiguity[];
  clarification_questions: ClarificationQuestion[];
  ai_run_id: string | null;
  analysis_status: string;
}

export interface Deadline {
  id: string;
  description: string;
  deadline: string;
  days_remaining: number;
  type: string;
  source_section?: string;
  certainty: string;
}

class APIService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await getErrorMessage(response);
      throw new Error(error || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Document Upload
  async uploadDocument(
    file: File,
    contractId?: string,
    contractName?: string
  ): Promise<{
    contract_id: string;
    version_id: string;
    version_number: number;
    file_name: string;
    file_type: string;
    text_length: number;
    metadata?: any;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    if (contractId) formData.append('contract_id', contractId);
    if (contractName) formData.append('contract_name', contractName);

    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Upload failed');
    }

    return response.json();
  }

  async pasteText(
    text: string,
    contractId?: string,
    contractName?: string
  ): Promise<{
    contract_id: string;
    version_id: string;
    version_number: number;
    text_length: number;
    metadata?: any;
  }> {
    const url = new URL(`${API_BASE}/documents/paste-text`, window.location.origin);
    if (contractName) {
      url.searchParams.append('contract_name', contractName);
    }

    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ contract_id: contractId, text }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Paste failed');
    }

    return response.json();
  }

  // Analysis
  async analyzeContract(contractVersionId: string): Promise<Analysis> {
    return this.request('/analysis/analyze', {
      method: 'POST',
      body: JSON.stringify({ contract_version_id: contractVersionId }),
    });
  }

  // Review
  async approveItem(
    itemId: string,
    itemType: 'extracted_item' | 'obligation',
    notes?: string
  ): Promise<{ id: string; review_status: string; user_edited: string; updated_at: string }> {
    return this.request('/review/approve', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, item_type: itemType, notes }),
    });
  }

  async rejectItem(
    itemId: string,
    itemType: 'extracted_item' | 'obligation',
    notes?: string
  ): Promise<{ id: string; review_status: string; user_edited: string; updated_at: string }> {
    return this.request('/review/reject', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, item_type: itemType, notes }),
    });
  }

  async editItem(
    itemId: string,
    itemType: 'extracted_item' | 'obligation',
    updates: Record<string, any>,
    notes?: string
  ): Promise<{ id: string; review_status: string; user_edited: string; updated_at: string }> {
    return this.request('/review/edit', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, item_type: itemType, updates, notes }),
    });
  }

  // Deadlines
  async calculateDeadlines(
    contractVersionId: string,
    daysAhead: number = 90,
    contractId?: string
  ): Promise<{ deadlines: Deadline[]; total: number }> {
    return this.request(`/deadlines/calculate?days_ahead=${daysAhead}`, {
      method: 'POST',
      body: JSON.stringify({
        contract_version_id: contractVersionId,
        contract_id: contractId,
      }),
    });
  }

  // Versions
  async getContractVersions(contractId: string): Promise<{ versions: ContractVersion[]; total: number }> {
    return this.request(`/versions/contract/${contractId}`);
  }

  async detectStaleItems(versionId: string): Promise<{
    stale_count: number;
    changed_fields: any[];
    previous_version: number;
    new_version: number;
  }> {
    return this.request(`/versions/detect-stale/${versionId}`, {
      method: 'POST',
    });
  }

  // Contracts
  async getContracts(): Promise<{ contracts: Contract[]; total: number }> {
    return this.request('/contracts');
  }

  async getContract(contractId: string): Promise<Contract> {
    return this.request(`/contracts/${contractId}`);
  }

  // Summary
  async generateSummary(contractVersionId: string): Promise<any> {
    return this.request('/analysis/summary', {
      method: 'POST',
      body: JSON.stringify({ contract_version_id: contractVersionId }),
    });
  }
}

export const api = new APIService();
