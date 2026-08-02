export type User = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};
