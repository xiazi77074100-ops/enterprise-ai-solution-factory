import { describe, expect, it } from "vitest";

import { checkFile, formatBytes } from "./DocumentsPanel";

const file = (name: string, size: number) => new File([new Uint8Array(size)], name);

describe("checkFile (same rules and wording as docs/design/detail/documents.md)", () => {
  it("requires a file", () => {
    expect(checkFile(null)).toBe("ファイルを選択してください。");
  });
  it("accepts PDF, PNG and JPEG by extension", () => {
    for (const name of ["a.pdf", "b.PNG", "c.jpg", "d.jpeg"]) expect(checkFile(file(name, 10))).toBeNull();
  });
  it("rejects other types, empty and too large files", () => {
    expect(checkFile(file("a.svg", 10))).toBe("PDF・PNG・JPEG のファイルを選択してください。");
    expect(checkFile(file("a.pdf.exe", 10))).toBe("PDF・PNG・JPEG のファイルを選択してください。");
    expect(checkFile(file("a.pdf", 0))).toBe("ファイルが空です。");
    expect(checkFile(file("a.pdf", 10 * 1024 * 1024 + 1))).toBe("ファイルの大きさは 10 MB 以内にしてください。");
  });
});

describe("formatBytes", () => {
  it("uses B, KB and MB", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
