"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  GripVertical,
  MoreVertical,
  Pencil,
  Trash2,
  Copy,
  Power,
  PowerOff,
  Code2,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { SQLTransformation, WriteMode } from "@/types/transformation";
import { cn } from "@/lib/utils";

interface TransformationListProps {
  transformations: SQLTransformation[];
  onEdit: (transformation: SQLTransformation) => void;
  onDelete: (transformationId: string) => void;
  onDuplicate: (transformationId: string) => void;
  onToggle: (transformationId: string, isActive: boolean) => void;
  onReorder: (transformationIds: string[]) => void;
  isReordering?: boolean;
}

interface SortableTransformationCardProps {
  transformation: SQLTransformation;
  onEdit: (transformation: SQLTransformation) => void;
  onDelete: (transformationId: string) => void;
  onDuplicate: (transformationId: string) => void;
  onToggle: (transformationId: string, isActive: boolean) => void;
  isDragging?: boolean;
}

function SortableTransformationCard({
  transformation,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle,
  isDragging,
}: SortableTransformationCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: transformation.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <TransformationCard
        transformation={transformation}
        onEdit={onEdit}
        onDelete={onDelete}
        onDuplicate={onDuplicate}
        onToggle={onToggle}
        dragHandleProps={{ ...attributes, ...listeners }}
        isDragging={isDragging}
      />
    </div>
  );
}

interface TransformationCardProps {
  transformation: SQLTransformation;
  onEdit: (transformation: SQLTransformation) => void;
  onDelete: (transformationId: string) => void;
  onDuplicate: (transformationId: string) => void;
  onToggle: (transformationId: string, isActive: boolean) => void;
  dragHandleProps?: any;
  isDragging?: boolean;
}

function TransformationCard({
  transformation,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle,
  dragHandleProps,
  isDragging,
}: TransformationCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const writeModeLabels: Record<WriteMode, string> = {
    replace: "Replace",
    append: "Append",
    merge: "Merge",
  };

  return (
    <>
      <Card
        className={cn(
          "group transition-all duration-200",
          !transformation.is_active && "opacity-60",
          isDragging && "shadow-lg ring-2 ring-primary/20"
        )}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            {/* Drag Handle */}
            <button
              className="flex-shrink-0 p-1.5 -ml-1 rounded-md hover:bg-muted cursor-grab active:cursor-grabbing touch-none"
              {...dragHandleProps}
            >
              <GripVertical className="h-5 w-5 text-muted-foreground" />
            </button>

            {/* Order Number */}
            <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm">
              {transformation.execution_order + 1}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold text-foreground truncate">
                      {transformation.name}
                    </h4>
                    <Badge
                      variant={transformation.is_active ? "success" : "secondary"}
                      className="text-xs"
                    >
                      {transformation.is_active ? "Active" : "Inactive"}
                    </Badge>
                    {transformation.continue_on_error && (
                      <Badge variant="warning" className="text-xs">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        Continue on Error
                      </Badge>
                    )}
                  </div>

                  {transformation.description && (
                    <p className="text-sm text-muted-foreground line-clamp-1">
                      {transformation.description}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                    {transformation.target_table && (
                      <span className="flex items-center gap-1">
                        <Code2 className="h-3 w-3" />
                        <span className="font-mono">{transformation.target_table}</span>
                        <span className="text-muted-foreground/70">
                          ({writeModeLabels[transformation.write_mode]})
                        </span>
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {transformation.timeout_seconds === 0
                        ? "No timeout"
                        : transformation.timeout_seconds >= 60
                        ? `${Math.floor(transformation.timeout_seconds / 60)}m`
                        : `${transformation.timeout_seconds}s`}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onEdit(transformation)}>
                      <Pencil className="h-4 w-4 mr-2" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onDuplicate(transformation.id)}>
                      <Copy className="h-4 w-4 mr-2" />
                      Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onToggle(transformation.id, !transformation.is_active)}
                    >
                      {transformation.is_active ? (
                        <>
                          <PowerOff className="h-4 w-4 mr-2" />
                          Deactivate
                        </>
                      ) : (
                        <>
                          <Power className="h-4 w-4 mr-2" />
                          Activate
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setShowDeleteDialog(true)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* SQL Preview */}
              <div className="mt-3 p-3 rounded-lg bg-muted/50 font-mono text-xs text-muted-foreground overflow-hidden">
                <pre className="whitespace-pre-wrap line-clamp-2">
                  {transformation.sql_query}
                </pre>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Transformation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{transformation.name}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onDelete(transformation.id);
                setShowDeleteDialog(false);
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function TransformationList({
  transformations,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle,
  onReorder,
  isReordering,
}: TransformationListProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  // Sort transformations by execution order
  const sortedTransformations = useMemo(
    () => [...transformations].sort((a, b) => a.execution_order - b.execution_order),
    [transformations]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);

      if (over && active.id !== over.id) {
        const oldIndex = sortedTransformations.findIndex((t) => t.id === active.id);
        const newIndex = sortedTransformations.findIndex((t) => t.id === over.id);

        const newOrder = arrayMove(sortedTransformations, oldIndex, newIndex);
        const newIds = newOrder.map((t) => t.id);
        onReorder(newIds);
      }
    },
    [sortedTransformations, onReorder]
  );

  const activeTransformation = activeId
    ? sortedTransformations.find((t) => t.id === activeId)
    : null;

  if (sortedTransformations.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Code2 className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="font-semibold text-lg mb-1">No Transformations</h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            Create your first SQL transformation to process and transform data after
            it's loaded to your destination.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={sortedTransformations.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="space-y-3">
          {sortedTransformations.map((transformation) => (
            <SortableTransformationCard
              key={transformation.id}
              transformation={transformation}
              onEdit={onEdit}
              onDelete={onDelete}
              onDuplicate={onDuplicate}
              onToggle={onToggle}
            />
          ))}
        </div>
      </SortableContext>

      <DragOverlay>
        {activeTransformation ? (
          <TransformationCard
            transformation={activeTransformation}
            onEdit={() => {}}
            onDelete={() => {}}
            onDuplicate={() => {}}
            onToggle={() => {}}
            isDragging
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default TransformationList;
