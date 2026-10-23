import '@testing-library/jest-dom/vitest'
class RO { observe() {} unobserve() {} disconnect() {} }
// @ts-ignore
globalThis.ResizeObserver = globalThis.ResizeObserver ?? RO
if (!window.matchMedia) {
  // @ts-ignore
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} })
}
