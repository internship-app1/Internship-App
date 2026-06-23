import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { FileUpload, createFileUploadItem, type FileUploadItem } from './motion/file-upload';

interface ResumeUploadFormProps {
  onSubmit: (file: File) => void;
  isLoading: boolean;
}

const ResumeUploadForm: React.FC<ResumeUploadFormProps> = ({ onSubmit, isLoading }) => {
  const [items, setItems] = useState<FileUploadItem[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const handleFilesAdded = (added: FileUploadItem[], files: File[]) => {
    // Only allow one file — replace any previous selection
    const item = { ...added[0], status: 'success' as const, progress: 100 };
    setItems([item]);
    setPendingFile(files[0] ?? null);
  };

  const handleValueChange = (next: FileUploadItem[]) => {
    setItems(next);
    if (next.length === 0) setPendingFile(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pendingFile) onSubmit(pendingFile);
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-4">
      <FileUpload
        value={items}
        onValueChange={handleValueChange}
        onFilesAdded={handleFilesAdded}
        accept=".pdf,.png,.jpg,.jpeg"
        multiple={false}
        maxFiles={1}
        disabled={isLoading}
        title="Drop your resume here"
        description="PDF, PNG or JPG — max 10 MB"
        browseLabel="Browse files"
      />

      <Button
        type="submit"
        className="w-full"
        disabled={!pendingFile || isLoading}
      >
        {isLoading ? (
          <>
            <Sparkles className="h-4 w-4 mr-2 animate-spin" />
            Analyzing…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4 mr-2" />
            See My Matches
          </>
        )}
      </Button>
    </form>
  );
};

export default ResumeUploadForm;
