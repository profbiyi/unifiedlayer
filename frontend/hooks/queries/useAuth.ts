"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api, { setToken, removeToken } from "@/lib/api-client";
import { LoginRequest, RegisterRequest, AuthResponse, User } from "@/types/auth";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";

interface UseLoginOptions {
  on2FARequired?: (tempToken: string) => void;
}

export const useLogin = (options?: UseLoginOptions) => {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      const formData = new URLSearchParams();
      formData.append("username", credentials.username);
      formData.append("password", credentials.password);

      const { data } = await api.post("/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });
      return data;
    },
    onSuccess: (data: any) => {
      if (data.requires_2fa) {
        options?.on2FARequired?.(data.temp_token);
        return;
      }

      // Store token in localStorage
      if (data.access_token) {
        setToken(data.access_token);
      }

      queryClient.setQueryData(["currentUser"], data.user);
      toast.success("Login successful!");
      router.push("/overview");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Login failed");
    },
  });
};

export const useVerify2FA = () => {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { temp_token: string; code: string }) => {
      const { data } = await api.post("/auth/2fa/verify", payload);
      return data;
    },
    onSuccess: (data: any) => {
      // Store token in localStorage
      if (data.access_token) {
        setToken(data.access_token);
      }

      queryClient.setQueryData(["currentUser"], data.user);
      toast.success("Login successful!");
      router.push("/overview");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Invalid verification code");
    },
  });
};

export const useRegister = () => {
  return useMutation({
    mutationFn: async (userData: RegisterRequest) => {
      const { data } = await api.post<User>("/auth/register", userData);
      return data;
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Registration failed");
    },
  });
};

export const useVerifyEmail = () => {
  return useMutation({
    mutationFn: async (token: string) => {
      const { data } = await api.post("/auth/verify-email", { token });
      return data;
    },
  });
};

export const useResendVerification = () => {
  return useMutation({
    mutationFn: async (email: string) => {
      const { data } = await api.post("/auth/resend-verification", { email });
      return data;
    },
    onSuccess: () => {
      toast.success("Verification email sent! Check your inbox.");
    },
    onError: () => {
      toast.error("Failed to resend verification email.");
    },
  });
};

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const { data } = await api.get<User>("/auth/me");
      return data;
    },
    retry: false,
  });
};

export const useLogout = () => {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      // Try to call backend logout (optional, mainly for cookie cleanup)
      try {
        await api.post("/auth/logout");
      } catch (e) {
        // Ignore errors - we'll clear local state anyway
      }
    },
    onSuccess: () => {
      removeToken();
      queryClient.clear();
      toast.success("Logged out successfully");
      router.push("/login");
    },
    onError: () => {
      // Even if backend call fails, clear client state
      removeToken();
      queryClient.clear();
      router.push("/login");
    },
  });
};
