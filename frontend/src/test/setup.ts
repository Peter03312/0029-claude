import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom 未实现滚动与对象 URL，统一打桩；具体调用断言由各用例自行覆盖。
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

if (typeof URL.createObjectURL !== "function") {
  URL.createObjectURL = vi.fn(() => "blob:mock");
}
if (typeof URL.revokeObjectURL !== "function") {
  URL.revokeObjectURL = vi.fn();
}
