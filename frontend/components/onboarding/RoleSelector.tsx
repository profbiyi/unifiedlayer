"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Rocket,
  Calculator,
  Settings,
  TrendingUp,
  Code,
  User,
  Check,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { RoleOption, UserRole } from "@/types/onboarding";
import { useSetRole } from "@/hooks/queries/useOnboarding";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  rocket: Rocket,
  calculator: Calculator,
  settings: Settings,
  "trending-up": TrendingUp,
  code: Code,
  user: User,
};

interface RoleSelectorProps {
  roles: RoleOption[];
  currentRole?: UserRole | null;
  onRoleSelected?: (role: UserRole) => void;
}

export function RoleSelector({ roles, currentRole, onRoleSelected }: RoleSelectorProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(currentRole || null);
  const { mutate: setRole, isPending } = useSetRole();

  const handleSelectRole = (role: UserRole) => {
    setSelectedRole(role);
  };

  const handleConfirm = () => {
    if (!selectedRole) return;

    setRole(selectedRole, {
      onSuccess: () => {
        onRoleSelected?.(selectedRole);
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">What&apos;s your role?</h2>
        <p className="text-muted-foreground">
          Help us personalize your experience with relevant features and recommendations.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map((role, index) => {
          const Icon = iconMap[role.icon] || User;
          const isSelected = selectedRole === role.value;

          return (
            <motion.button
              key={role.value}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => handleSelectRole(role.value as UserRole)}
              className={cn(
                "relative p-6 rounded-xl border-2 text-left transition-all",
                "hover:border-primary/50 hover:bg-accent/50",
                "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card"
              )}
            >
              {isSelected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute top-3 right-3"
                >
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                    <Check className="w-4 h-4 text-primary-foreground" />
                  </div>
                </motion.div>
              )}

              <div
                className={cn(
                  "w-12 h-12 rounded-lg flex items-center justify-center mb-4",
                  isSelected ? "bg-primary text-primary-foreground" : "bg-muted"
                )}
              >
                <Icon className="w-6 h-6" />
              </div>

              <h3 className="font-semibold mb-1">{role.label}</h3>
              <p className="text-sm text-muted-foreground">{role.description}</p>
            </motion.button>
          );
        })}
      </div>

      <div className="flex justify-center pt-4">
        <Button
          size="lg"
          onClick={handleConfirm}
          disabled={!selectedRole || isPending}
          className="min-w-[200px]"
        >
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </div>
    </div>
  );
}
