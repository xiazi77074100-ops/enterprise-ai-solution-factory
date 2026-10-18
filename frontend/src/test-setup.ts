import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver; Truncate only needs the callback shape.
class ResizeObserverStub {
  observe(): void {}
  disconnect(): void {}
  unobserve(): void {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
