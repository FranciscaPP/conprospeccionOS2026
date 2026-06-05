"use client";

import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface DemoDisabledButtonProps {
  children: ReactNode;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
}

export function DemoDisabledButton({
  children,
  variant = "outline",
  size = "sm",
  className,
}: DemoDisabledButtonProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger render={<span className="inline-flex" />}>
          <Button variant={variant} size={size} className={className} disabled>
            {children}
          </Button>
        </TooltipTrigger>
        <TooltipContent>Disponible en próxima versión</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

