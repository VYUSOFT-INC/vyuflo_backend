// src/utils/uiSession.ts

export interface UiSession {
  first_name: string;
  last_name:  string;
  email:      string;
  profile:    string | null;
  roles:      string[];
}
export function getUiSession(): UiSession | null {
  const match = document.cookie
    .split('; ')
    .find(row => row.startsWith('ui_session='));

  if (!match) return null;

  try {
    let raw = match.split('=').slice(1).join('=');

    // Decode URI encoding first
    raw = decodeURIComponent(raw);

    // Then strip surrounding quotes FastAPI adds
    if (raw.startsWith('"') && raw.endsWith('"')) {
      raw = raw.slice(1, -1);
    }

    const decoded = atob(raw);
    return JSON.parse(decoded) as UiSession;
  } catch {
    return null;
  }
}

export function updateUiSessionProfile(newProfilePath: string): void {
  const session = getUiSession();
  if (!session) return;

  session.profile = newProfilePath;
  const maxAge = 60 * 60 * 24 * 7;
  // base64 encode to stay consistent with backend
  const encoded = btoa(JSON.stringify(session));
  document.cookie = `ui_session=${encoded}; path=/; max-age=${maxAge}; samesite=lax`;

  window.dispatchEvent(new Event('ui-session-updated'));
}