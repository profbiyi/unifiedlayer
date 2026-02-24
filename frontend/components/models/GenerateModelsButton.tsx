"use client";

import { useState } from "react";
import { useGenerateModels } from "@/hooks/queries/useModels";
import { usePipelines } from "@/hooks/queries/usePipelines";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sparkles, Loader2, CheckCircle, Boxes } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface GenerateModelsButtonProps {
  pipelineId?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
  className?: string;
}

export function GenerateModelsButton({
  pipelineId: initialPipelineId,
  variant = "default",
  size = "default",
  className,
}: GenerateModelsButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>(
    initialPipelineId || ""
  );
  const [showSuccess, setShowSuccess] = useState(false);

  const { data: pipelines, isLoading: pipelinesLoading } = usePipelines();
  const generateModels = useGenerateModels();

  const handleGenerate = async () => {
    if (!selectedPipelineId) return;

    try {
      await generateModels.mutateAsync(selectedPipelineId);
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        setIsOpen(false);
      }, 2000);
    } catch (error) {
      // Error handled by the mutation
    }
  };

  const activePipelines = pipelines?.filter((p) => p.is_active) || [];

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant={variant} size={size} className={className}>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Models
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <AnimatePresence mode="wait">
          {showSuccess ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center justify-center py-8"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 10 }}
                className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mb-4"
              >
                <CheckCircle className="h-8 w-8 text-success" />
              </motion.div>
              <h3 className="text-lg font-semibold mb-2">Models Generated!</h3>
              <p className="text-sm text-muted-foreground text-center">
                AI has analyzed your data and created dimensional models.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Boxes className="h-5 w-5 text-primary" />
                  Generate AI Models
                </DialogTitle>
                <DialogDescription>
                  Use AI to automatically generate dimensional models (star
                  schema) from your synced data. This will analyze your tables
                  and create fact and dimension tables.
                </DialogDescription>
              </DialogHeader>

              <div className="py-6 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Select Pipeline</label>
                  {initialPipelineId ? (
                    <p className="text-sm text-muted-foreground">
                      Generating models for the current pipeline
                    </p>
                  ) : (
                    <Select
                      value={selectedPipelineId}
                      onValueChange={setSelectedPipelineId}
                      disabled={pipelinesLoading}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a pipeline..." />
                      </SelectTrigger>
                      <SelectContent>
                        {activePipelines.map((pipeline) => (
                          <SelectItem key={pipeline.id} value={pipeline.id}>
                            {pipeline.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>

                <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    What AI will do:
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>- Analyze source table schemas and data patterns</li>
                    <li>- Identify fact and dimension relationships</li>
                    <li>- Generate SQL definitions for star schema</li>
                    <li>- Create business questions the model can answer</li>
                  </ul>
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleGenerate}
                  disabled={
                    !selectedPipelineId ||
                    generateModels.isPending ||
                    pipelinesLoading
                  }
                >
                  {generateModels.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate Models
                    </>
                  )}
                </Button>
              </DialogFooter>
            </motion.div>
          )}
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  );
}

export default GenerateModelsButton;
