"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import ConnectorPicker from "@/components/connect/ConnectorPicker";
import CredentialForm from "@/components/connect/CredentialForm";
import DestinationPicker from "@/components/connect/DestinationPicker";
import PipelineConfirm from "@/components/connect/PipelineConfirm";
import { slideUp } from "@/lib/animations";
import { getSourceMeta, getDestinationMeta } from "@/lib/connector-icons";
import { useCreateSource } from "@/hooks/queries/useSources";
import { useCreateDestination } from "@/hooks/queries/useDestinations";
import { useCreatePipeline, useTriggerPipeline } from "@/hooks/queries/usePipelines";
import toast from "react-hot-toast";
import {
  ArrowLeft,
  CheckCircle2,
  Rocket,
  PartyPopper,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import type { Destination, WriteMode } from "@/types/pipeline";

type Step = "source" | "credentials" | "destination" | "confirm" | "success";

export default function ConnectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ── State ──
  const [step, setStep] = useState<Step>("source");
  const [sourceType, setSourceType] = useState(searchParams.get("source") || "");
  const [sourceCredentials, setSourceCredentials] = useState<Record<string, string>>({});
  const [sourceTestPassed, setSourceTestPassed] = useState(false);
  const [sourceName, setSourceName] = useState("");

  const [existingDestinationId, setExistingDestinationId] = useState("");
  const [newDestType, setNewDestType] = useState("");
  const [destCredentials, setDestCredentials] = useState<Record<string, string>>({});
  const [destTestPassed, setDestTestPassed] = useState(false);
  const [destName, setDestName] = useState("");

  const [pipelineName, setPipelineName] = useState("");
  const [schedule, setSchedule] = useState("0 6 * * *"); // daily by default
  const [writeMode, setWriteMode] = useState<WriteMode>("merge");

  const [createdPipelineId, setCreatedPipelineId] = useState("");

  // ── Mutations ──
  const createSource = useCreateSource();
  const createDestination = useCreateDestination();
  const createPipeline = useCreatePipeline();
  const triggerPipeline = useTriggerPipeline();

  // Pre-select source from URL param
  useEffect(() => {
    const src = searchParams.get("source");
    if (src) {
      setSourceType(src);
      setStep("credentials");
    }
  }, [searchParams]);

  // Auto-generate pipeline name
  useEffect(() => {
    if (sourceType && (existingDestinationId || newDestType)) {
      const srcMeta = getSourceMeta(sourceType);
      const dstMeta = existingDestinationId
        ? null // we'll use the existing name
        : getDestinationMeta(newDestType);
      const srcName = srcMeta?.name || sourceType;
      const dstName = dstMeta?.name || newDestType || "Destination";
      setPipelineName(`${srcName} → ${dstName}`);
    }
  }, [sourceType, existingDestinationId, newDestType]);

  // Auto-generate source name
  useEffect(() => {
    if (sourceType) {
      const meta = getSourceMeta(sourceType);
      setSourceName(meta?.name || sourceType);
    }
  }, [sourceType]);

  // Auto-generate destination name
  useEffect(() => {
    if (newDestType) {
      const meta = getDestinationMeta(newDestType);
      setDestName(meta?.name || newDestType);
    }
  }, [newDestType]);

  // ── Handlers ──
  const handleSourceSelect = (id: string) => {
    setSourceType(id);
    setSourceCredentials({});
    setSourceTestPassed(false);
    setStep("credentials");
  };

  const handleSourceTestResult = (success: boolean) => {
    setSourceTestPassed(success);
  };

  const handleSelectExistingDest = (dest: Destination) => {
    setExistingDestinationId(dest.id);
    setNewDestType("");
    setDestTestPassed(true);
    setStep("confirm");
  };

  const handleDestTestResult = (success: boolean) => {
    setDestTestPassed(success);
  };

  const handleSubmit = async () => {
    try {
      // 1. Create source
      const sourceResult = await createSource.mutateAsync({
        name: sourceName,
        source_type: sourceType,
        config: sourceCredentials,
        is_active: true,
      } as any);

      const sourceId = sourceResult.source?.id || (sourceResult as any).id;

      // 2. Create destination if new
      let destinationId = existingDestinationId;
      if (!destinationId && newDestType) {
        const destResult = await createDestination.mutateAsync({
          name: destName,
          destination_type: newDestType,
          config: destCredentials,
          is_active: true,
        } as any);

        destinationId = (destResult as any).id;
      }

      if (!destinationId) {
        toast.error("Please select or create a destination");
        return;
      }

      // 3. Create pipeline
      const pipeline = await createPipeline.mutateAsync({
        name: pipelineName,
        source_id: sourceId,
        destination_id: destinationId,
        schedule: schedule || undefined,
        is_active: true,
        write_mode: writeMode,
        schema_contract: "evolve",
      });

      setCreatedPipelineId((pipeline as any).id);

      // 4. Trigger first run
      try {
        await triggerPipeline.mutateAsync((pipeline as any).id);
      } catch {
        // Non-critical — pipeline created but first run failed
      }

      setStep("success");

      // Fire confetti
      window.dispatchEvent(new CustomEvent("unifiedlayer:first-run"));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Something went wrong. Please try again.");
    }
  };

  const isSubmitting =
    createSource.isPending || createDestination.isPending || createPipeline.isPending;

  // ── Step navigation ──
  const steps: Step[] = ["source", "credentials", "destination", "confirm"];
  const currentIndex = steps.indexOf(step);

  const goBack = () => {
    if (step === "credentials") setStep("source");
    else if (step === "destination") setStep("credentials");
    else if (step === "confirm") setStep("destination");
  };

  const goNext = () => {
    if (step === "credentials" && sourceTestPassed) setStep("destination");
    else if (step === "destination" && (existingDestinationId || destTestPassed)) setStep("confirm");
  };

  const canProceed = () => {
    if (step === "credentials") return sourceTestPassed;
    if (step === "destination") return existingDestinationId || destTestPassed;
    return false;
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-12">
      {/* Back + Header */}
      {step !== "success" && (
        <div className="flex items-center gap-4">
          {step !== "source" && (
            <Button variant="ghost" size="sm" onClick={goBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          )}
          <div className="flex-1" />
          {/* Progress dots */}
          <div className="flex items-center gap-2">
            {steps.map((s, i) => (
              <div
                key={s}
                className={`h-2 rounded-full transition-all ${
                  i <= currentIndex
                    ? "w-8 bg-primary"
                    : "w-2 bg-muted"
                }`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Step content */}
      <AnimatePresence mode="wait">
        {step === "source" && (
          <motion.div key="source" variants={slideUp} initial="initial" animate="animate" exit="exit">
            <ConnectorPicker
              mode="source"
              selected={sourceType}
              onSelect={handleSourceSelect}
            />
          </motion.div>
        )}

        {step === "credentials" && (
          <motion.div key="credentials" variants={slideUp} initial="initial" animate="animate" exit="exit">
            <div className="space-y-6">
              <div className="text-center space-y-2">
                <h2 className="text-2xl font-bold tracking-tight">Connect your account</h2>
                <p className="text-muted-foreground">
                  Enter your credentials — we&apos;ll test them automatically
                </p>
              </div>

              <Card className="max-w-lg mx-auto">
                <CardContent className="pt-6">
                  <CredentialForm
                    connectorId={sourceType}
                    mode="source"
                    values={sourceCredentials}
                    onChange={setSourceCredentials}
                    onTestResult={handleSourceTestResult}
                    autoTest={true}
                  />
                </CardContent>
              </Card>

              {/* Next button */}
              <div className="flex justify-center">
                <Button
                  size="lg"
                  onClick={goNext}
                  disabled={!sourceTestPassed}
                  className="h-11 px-8 rounded-xl"
                >
                  Continue
                  <ArrowLeft className="ml-2 h-4 w-4 rotate-180" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {step === "destination" && (
          <motion.div key="destination" variants={slideUp} initial="initial" animate="animate" exit="exit">
            <DestinationPicker
              selectedExistingId={existingDestinationId}
              selectedNewType={newDestType}
              newCredentials={destCredentials}
              onSelectExisting={handleSelectExistingDest}
              onSelectNewType={(type) => {
                setNewDestType(type);
                setExistingDestinationId("");
                setDestTestPassed(false);
              }}
              onCredentialsChange={setDestCredentials}
              onTestResult={handleDestTestResult}
            />
            {/* Next button for new destinations */}
            {newDestType && destTestPassed && !existingDestinationId && (
              <div className="flex justify-center mt-6">
                <Button
                  size="lg"
                  onClick={() => setStep("confirm")}
                  className="h-11 px-8 rounded-xl"
                >
                  Continue
                  <ArrowLeft className="ml-2 h-4 w-4 rotate-180" />
                </Button>
              </div>
            )}
          </motion.div>
        )}

        {step === "confirm" && (
          <motion.div key="confirm" variants={slideUp} initial="initial" animate="animate" exit="exit">
            <PipelineConfirm
              sourceType={sourceType}
              destinationType={existingDestinationId ? "" : newDestType}
              pipelineName={pipelineName}
              schedule={schedule}
              writeMode={writeMode}
              onNameChange={setPipelineName}
              onScheduleChange={setSchedule}
              onWriteModeChange={setWriteMode}
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
            />
          </motion.div>
        )}

        {step === "success" && (
          <motion.div
            key="success"
            variants={slideUp}
            initial="initial"
            animate="animate"
            className="text-center space-y-6 py-12"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
              className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30"
            >
              <PartyPopper className="h-10 w-10 text-emerald-600 dark:text-emerald-400" />
            </motion.div>

            <div className="space-y-2">
              <h2 className="text-3xl font-bold">Your data is syncing!</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                We&apos;ve created your pipeline and kicked off the first sync.
                You can track progress in real-time.
              </p>
            </div>

            <div className="flex items-center justify-center gap-3">
              <Link href={`/pipelines/${createdPipelineId}`}>
                <Button size="lg" className="h-11 rounded-xl gap-2">
                  <Rocket className="h-4 w-4" />
                  View Pipeline
                </Button>
              </Link>
              <Link href="/connect">
                <Button variant="outline" size="lg" className="h-11 rounded-xl gap-2">
                  Connect Another
                </Button>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
