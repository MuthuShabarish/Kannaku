const API_BASE = import.meta.env.VITE_API_URL || '';

function getAuthHeader() {
  const token = localStorage.getItem('kanakku_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(response) {
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail?.message || data?.message || 'Request failed';
    const errorCode = data?.error?.code || 'API_ERROR';
    const err = new Error(errorMsg);
    err.code = errorCode;
    err.status = response.status;
    err.details = data?.error?.details || data;
    throw err;
  }

  return data;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return handleResponse(res);
  },

  async register(payload) {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async login(payload) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async getOnboardingState() {
    const res = await fetch(`${API_BASE}/api/v1/onboarding`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async saveOnboardingDraft(payload) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/draft`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getRecommendation(answers) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(answers),
    });
    return handleResponse(res);
  },

  async completeOnboarding(payload) {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async getBusinessProfile() {
    const res = await fetch(`${API_BASE}/api/v1/business/profile`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse(res);
  },

  async updateBusinessPreferences(payload) {
    const res = await fetch(`${API_BASE}/api/v1/business/preferences`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async logout() {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          ...getAuthHeader(),
        },
      });
    } finally {
      localStorage.removeItem('kanakku_token');
    }
  },
};
