export interface Organization {
  id: number;
  name: string;
  slug: string;
  logo_url?: string;
  subscription_plan?: string;
  current_user_count?: number;
  max_users?: number;
  is_active?: boolean;
  can_sync_data?: boolean;
  admin_onboarded?: boolean;
  admin_onboarded_at?: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  organization_id: number;
  organization?: Organization;
  roles?: string[];
  invitation_status?: string | null;
  invitation_expires_at?: string | null;
  invitation_accepted_at?: string | null;
  two_factor_enabled?: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
