import { useRef } from "react";

interface ImportPanelProps {
  title: string;
  hint: string;
  accept: string;
  fileName: string | null;
  error: { code: string; message: string } | null;
  onSelect: (file: File) => void;
  testId: string;
}

/** 单侧导入区：选择文件并在本区内展示解析/契约错误（整单拒绝）。 */
export function ImportPanel({ title, hint, accept, fileName, error, onSelect, testId }: ImportPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <section className={`panel import-panel${error ? " has-error" : ""}`} data-testid={testId}>
      <h2>{title}</h2>
      <p className="hint">{hint}</p>
      <div className="file-row">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          data-testid={`${testId}-input`}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onSelect(file);
            // 允许重新选择同名文件
            event.target.value = "";
          }}
        />
        {fileName && <span className="file-name" title={fileName}>{fileName}</span>}
      </div>
      {error && (
        <div className="error-box" role="alert" data-testid={`${testId}-error`}>
          <span className="code">[{error.code}]</span>
          {error.message}
        </div>
      )}
    </section>
  );
}
