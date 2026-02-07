"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  HelpCircle,
} from "lucide-react";
import { DbtProject, CreateDbtProjectRequest } from "@/types/dbt";
import {
  useCreateDbtProject,
  useUpdateDbtProject,
  useTestDbtConnection,
} from "@/hooks/queries/useDbt";

interface DbtProjectFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project?: DbtProject | null;
}

const TARGET_PROFILES = [
  { value: "dev", label: "Development" },
  { value: "staging", label: "Staging" },
  { value: "prod", label: "Production" },
];

export default function DbtProjectForm({
  open,
  onOpenChange,
  project,
}: DbtProjectFormProps) {
  const isEditing = !!project;

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [gitRepoUrl, setGitRepoUrl] = useState("");
  const [gitBranch, setGitBranch] = useState("main");
  const [gitUsername, setGitUsername] = useState("");
  const [gitToken, setGitToken] = useState("");
  const [targetProfile, setTargetProfile] = useState("dev");
  const [defaultModels, setDefaultModels] = useState("");

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "idle" | "testing" | "success" | "error"
  >("idle");
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);

  const createProject = useCreateDbtProject();
  const updateProject = useUpdateDbtProject(project?.id || "");
  const testConnection = useTestDbtConnection();

  // Reset form when dialog opens/closes or project changes
  useEffect(() => {
    if (open) {
      if (project) {
        setName(project.name);
        setDescription(project.description || "");
        setGitRepoUrl(project.git_repo_url);
        setGitBranch(project.git_branch);
        setGitUsername(project.git_username || "");
        setGitToken(""); // Never pre-fill token
        setTargetProfile(project.target_profile);
        setDefaultModels(project.default_models?.join(", ") || "");
      } else {
        setName("");
        setDescription("");
        setGitRepoUrl("");
        setGitBranch("main");
        setGitUsername("");
        setGitToken("");
        setTargetProfile("dev");
        setDefaultModels("");
      }
      setConnectionStatus("idle");
      setAvailableBranches([]);
      setShowAdvanced(false);
      setShowToken(false);
    }
  }, [open, project]);

  const handleTestConnection = async () => {
    setConnectionStatus("testing");
    try {
      const result = await testConnection.mutateAsync({
        git_repo_url: gitRepoUrl,
        git_username: gitUsername || undefined,
        git_token: gitToken || undefined,
      });
      if (result.success) {
        setConnectionStatus("success");
        if (result.branches) {
          setAvailableBranches(result.branches);
        }
      } else {
        setConnectionStatus("error");
      }
    } catch {
      setConnectionStatus("error");
    }
  };

  const handleSubmit = async () => {
    const modelsArray = defaultModels
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean);

    const data: CreateDbtProjectRequest = {
      name,
      description: description || undefined,
      git_repo_url: gitRepoUrl,
      git_branch: gitBranch,
      git_username: gitUsername || undefined,
      git_token: gitToken || undefined,
      target_profile: targetProfile,
      default_models: modelsArray.length > 0 ? modelsArray : undefined,
    };

    try {
      if (isEditing) {
        await updateProject.mutateAsync(data);
      } else {
        await createProject.mutateAsync(data);
      }
      onOpenChange(false);
    } catch {
      // Error handled by mutation
    }
  };

  const isSubmitting = createProject.isPending || updateProject.isPending;
  const canSubmit = name && gitRepoUrl && gitBranch && targetProfile;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Edit dbt Project" : "Add dbt Project"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update your dbt project configuration."
              : "Connect a dbt project from a Git repository."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Info */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="e.g., Analytics Transformations"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A friendly name to identify this project
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="What does this dbt project do?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          {/* Git Configuration */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h4 className="font-medium">Git Repository</h4>
              <span className="text-xs text-muted-foreground">
                (where your dbt project lives)
              </span>
            </div>

            <div className="space-y-2">
              <Label htmlFor="gitRepoUrl">Repository URL</Label>
              <Input
                id="gitRepoUrl"
                placeholder="https://github.com/org/repo.git"
                value={gitRepoUrl}
                onChange={(e) => {
                  setGitRepoUrl(e.target.value);
                  setConnectionStatus("idle");
                }}
              />
              <p className="text-xs text-muted-foreground">
                HTTPS URL to your Git repository
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="gitUsername">Git Username (optional)</Label>
                <Input
                  id="gitUsername"
                  placeholder="username or email"
                  value={gitUsername}
                  onChange={(e) => setGitUsername(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="gitToken">Access Token (optional)</Label>
                  <span title="Personal access token or deploy key for private repos">
                    <HelpCircle className="h-3 w-3 text-muted-foreground" />
                  </span>
                </div>
                <div className="relative">
                  <Input
                    id="gitToken"
                    type={showToken ? "text" : "password"}
                    placeholder="ghp_xxxx..."
                    value={gitToken}
                    onChange={(e) => setGitToken(e.target.value)}
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowToken(!showToken)}
                  >
                    {showToken ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                {isEditing && (
                  <p className="text-xs text-muted-foreground">
                    Leave blank to keep existing token
                  </p>
                )}
              </div>
            </div>

            {/* Test Connection Button */}
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={handleTestConnection}
                disabled={!gitRepoUrl || connectionStatus === "testing"}
              >
                {connectionStatus === "testing" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  "Test Connection"
                )}
              </Button>
              {connectionStatus === "success" && (
                <span className="flex items-center text-sm text-green-600">
                  <CheckCircle2 className="mr-1 h-4 w-4" />
                  Connected
                </span>
              )}
              {connectionStatus === "error" && (
                <span className="flex items-center text-sm text-destructive">
                  <XCircle className="mr-1 h-4 w-4" />
                  Connection failed
                </span>
              )}
            </div>

            {/* Branch Selection */}
            <div className="space-y-2">
              <Label htmlFor="gitBranch">Branch</Label>
              {availableBranches.length > 0 ? (
                <Select value={gitBranch} onValueChange={setGitBranch}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a branch" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableBranches.map((branch) => (
                      <SelectItem key={branch} value={branch}>
                        {branch}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id="gitBranch"
                  placeholder="main"
                  value={gitBranch}
                  onChange={(e) => setGitBranch(e.target.value)}
                />
              )}
              <p className="text-xs text-muted-foreground">
                The branch containing your dbt project files
              </p>
            </div>
          </div>

          {/* dbt Configuration */}
          <div className="space-y-4">
            <h4 className="font-medium">dbt Configuration</h4>

            <div className="space-y-2">
              <Label htmlFor="targetProfile">Target Profile</Label>
              <Select value={targetProfile} onValueChange={setTargetProfile}>
                <SelectTrigger>
                  <SelectValue placeholder="Select target" />
                </SelectTrigger>
                <SelectContent>
                  {TARGET_PROFILES.map((profile) => (
                    <SelectItem key={profile.value} value={profile.value}>
                      {profile.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                The dbt profile target to use when running
              </p>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="border rounded-lg">
            <button
              type="button"
              className="flex items-center justify-between w-full p-4 text-left"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span className="font-medium">Advanced Options</span>
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            {showAdvanced && (
              <div className="px-4 pb-4 space-y-4 border-t pt-4">
                <div className="space-y-2">
                  <Label htmlFor="defaultModels">Default Models</Label>
                  <Input
                    id="defaultModels"
                    placeholder="staging.*, marts.dim_users, +marts.fct_orders+"
                    value={defaultModels}
                    onChange={(e) => setDefaultModels(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated list of models or selectors to run by default.
                    Leave empty to run all models.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isEditing ? "Saving..." : "Creating..."}
              </>
            ) : isEditing ? (
              "Save Changes"
            ) : (
              "Create Project"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
