"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import ConnectorCard from "./ConnectorCard";
import CredentialForm from "./CredentialForm";
import { slideUp } from "@/lib/animations";
import { useDestinations } from "@/hooks/queries/useDestinations";
import { DESTINATION_CONNECTORS, getDestinationMeta } from "@/lib/connector-icons";
import {
  CheckCircle2,
  Plus,
  HardDrive,
  ArrowLeft,
} from "lucide-react";
import type { Destination } from "@/types/pipeline";

interface DestinationPickerProps {
  /** An already-selected existing destination ID (from the user's account). */
  selectedExistingId?: string;
  /** Selected destination type when creating new. */
  selectedNewType?: string;
  /** Credential values when creating a new destination. */
  newCredentials: Record<string, string>;
  /** Called when user selects an existing destination. */
  onSelectExisting: (dest: Destination) => void;
  /** Called when user picks a new destination type. */
  onSelectNewType: (type: string) => void;
  /** Called when credential fields change. */
  onCredentialsChange: (values: Record<string, string>) => void;
  /** Called when connection test completes. */
  onTestResult?: (success: boolean) => void;
}

export default function DestinationPicker({
  selectedExistingId,
  selectedNewType,
  newCredentials,
  onSelectExisting,
  onSelectNewType,
  onCredentialsChange,
  onTestResult,
}: DestinationPickerProps) {
  const { data: destinations, isLoading } = useDestinations();
  const [showNew, setShowNew] = useState(false);

  const existingDestinations = destinations || [];
  const hasExisting = existingDestinations.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Where should your data go?</h2>
        <p className="text-muted-foreground">
          {hasExisting
            ? "Pick an existing destination or create a new one"
            : "Choose a destination for your data"}
        </p>
      </div>

      {/* Existing destinations */}
      {hasExisting && !showNew && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground">YOUR DESTINATIONS</h3>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {existingDestinations.map((dest) => {
              const meta = getDestinationMeta(dest.destination_type || dest.type);
              const Icon = meta?.icon || HardDrive;
              const isSelected = selectedExistingId === dest.id;

              return (
                <motion.button
                  key={dest.id}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSelectExisting(dest)}
                  className={`
                    flex items-center gap-3 rounded-xl border p-4 text-left transition-all
                    ${isSelected
                      ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                      : "border-border hover:border-primary/30 hover:bg-accent/50"
                    }
                  `}
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${meta?.color || "bg-gray-500"}`}>
                    <Icon className={`h-5 w-5 ${meta?.textColor || "text-white"}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">{dest.name}</p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {dest.destination_type || dest.type}
                    </p>
                  </div>
                  {isSelected && (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-primary" />
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Add new button */}
          <Button
            variant="outline"
            className="w-full h-12 rounded-xl border-dashed"
            onClick={() => setShowNew(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add New Destination
          </Button>
        </div>
      )}

      {/* New destination picker */}
      {(showNew || !hasExisting) && (
        <AnimatePresence>
          <motion.div
            variants={slideUp}
            initial="initial"
            animate="animate"
            className="space-y-6"
          >
            {hasExisting && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowNew(false);
                  onSelectNewType("");
                }}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to existing
              </Button>
            )}

            {!selectedNewType ? (
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
                {DESTINATION_CONNECTORS.map((dest) => (
                  <ConnectorCard
                    key={dest.id}
                    connector={dest}
                    onClick={() => onSelectNewType(dest.id)}
                  />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <CredentialForm
                    connectorId={selectedNewType}
                    mode="destination"
                    values={newCredentials}
                    onChange={onCredentialsChange}
                    onTestResult={(success) => onTestResult?.(success)}
                    autoTest={true}
                  />
                </CardContent>
              </Card>
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
