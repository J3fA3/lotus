import React from 'react';
import { Editor } from '@tiptap/react';
import { Button } from './ui/button';

interface TableMenuProps {
  editor: Editor;
}

export const TableMenu: React.FC<TableMenuProps> = ({ editor }) => {
  if (!editor) return null;

  return (
    <div className="flex items-center gap-1 p-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().addRowBefore().run()}
        className="h-8 px-2 text-xs"
        title="Add row above"
      >
        ↑ Row
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().addRowAfter().run()}
        className="h-8 px-2 text-xs"
        title="Add row below"
      >
        ↓ Row
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().deleteRow().run()}
        className="h-8 px-2 text-xs text-red-600 hover:text-red-700"
        title="Delete row"
      >
        ✕ Row
      </Button>
      <div className="w-px h-6 bg-gray-300 dark:bg-gray-600" />
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().addColumnBefore().run()}
        className="h-8 px-2 text-xs"
        title="Add column left"
      >
        ← Col
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().addColumnAfter().run()}
        className="h-8 px-2 text-xs"
        title="Add column right"
      >
        → Col
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().deleteColumn().run()}
        className="h-8 px-2 text-xs text-red-600 hover:text-red-700"
        title="Delete column"
      >
        ✕ Col
      </Button>
      <div className="w-px h-6 bg-gray-300 dark:bg-gray-600" />
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().deleteTable().run()}
        className="h-8 px-2 text-xs text-red-600 hover:text-red-700"
        title="Delete table"
      >
        ✕ Table
      </Button>
    </div>
  );
};
