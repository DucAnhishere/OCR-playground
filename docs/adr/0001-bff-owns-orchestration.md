# ADR 0001: BFF Owns OCR Workflow Orchestration

## Status

Accepted

## Context

The earlier VietOCR path made the PyTorch OCR service call the Paddle service directly for layout detection. That created a hidden service dependency and split workflow ownership between the BFF and a model runtime container.

## Decision

The BFF is the only component that coordinates multi-service OCR workflows. For VietOCR, the BFF calls `paddle_structure` first, then sends the resulting layout boxes to the PyTorch service for recognition.

## Consequences

- Runtime services have clearer responsibilities.
- The service dependency graph is simpler: model services do not call each other.
- Hybrid workflow errors are reported from one orchestration layer.

