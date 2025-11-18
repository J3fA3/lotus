import React, { useEffect } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { CodeBlockLowlight } from '@tiptap/extension-code-block-lowlight';
import { Placeholder } from '@tiptap/extension-placeholder';
import { common, createLowlight } from 'lowlight';
import { ReactRenderer } from '@tiptap/react';
import tippy, { Instance as TippyInstance } from 'tippy.js';
import Suggestion from '@tiptap/suggestion';

import { SlashCommandMenu, MenuItem } from './RichTextEditorMenu';
import { WordArt, WORD_ART_STYLES } from './WordArtExtension';
import './rich-text-editor.css';

const lowlight = createLowlight(common);

interface RichTextEditorProps {
  content?: string;
  onChange?: (content: string) => void;
  placeholder?: string;
  variant?: 'minimal' | 'full';
  className?: string;
  autoFocus?: boolean;
}

// Slash command configuration
const getMenuItems = (editor: Editor): MenuItem[] => {
  const items: MenuItem[] = [
    // Headings
    {
      title: 'Heading 1',
      description: 'Large section heading',
      icon: 'H1',
      keywords: ['h1', 'heading', 'title', 'large'],
      command: (editor) => {
        editor.chain().focus().toggleHeading({ level: 1 }).run();
      },
    },
    {
      title: 'Heading 2',
      description: 'Medium section heading',
      icon: 'H2',
      keywords: ['h2', 'heading', 'subtitle', 'medium'],
      command: (editor) => {
        editor.chain().focus().toggleHeading({ level: 2 }).run();
      },
    },
    {
      title: 'Heading 3',
      description: 'Small section heading',
      icon: 'H3',
      keywords: ['h3', 'heading', 'small'],
      command: (editor) => {
        editor.chain().focus().toggleHeading({ level: 3 }).run();
      },
    },

    // Lists
    {
      title: 'Bullet List',
      description: 'Create a bullet point list',
      icon: '•',
      keywords: ['bullet', 'list', 'ul', 'unordered'],
      command: (editor) => {
        editor.chain().focus().toggleBulletList().run();
      },
    },
    {
      title: 'Numbered List',
      description: 'Create a numbered list',
      icon: '1.',
      keywords: ['number', 'list', 'ol', 'ordered'],
      command: (editor) => {
        editor.chain().focus().toggleOrderedList().run();
      },
    },

    // Code
    {
      title: 'Code Block',
      description: 'Insert a code block with syntax highlighting',
      icon: '</>',
      keywords: ['code', 'block', 'programming', 'syntax'],
      command: (editor) => {
        editor.chain().focus().toggleCodeBlock().run();
      },
    },

    // Quote
    {
      title: 'Quote',
      description: 'Insert a blockquote',
      icon: '"',
      keywords: ['quote', 'blockquote', 'citation'],
      command: (editor) => {
        editor.chain().focus().toggleBlockquote().run();
      },
    },

    // Divider
    {
      title: 'Divider',
      description: 'Insert a horizontal line',
      icon: '—',
      keywords: ['divider', 'line', 'hr', 'separator'],
      command: (editor) => {
        editor.chain().focus().setHorizontalRule().run();
      },
    },
  ];

  // Add Word Art styles (fun feature!)
  WORD_ART_STYLES.forEach((style) => {
    items.push({
      title: `Word Art: ${style.name}`,
      description: 'Retro-styled text formatting',
      icon: style.preview,
      keywords: ['wordart', 'word', 'art', 'style', 'retro', style.name.toLowerCase()],
      command: (editor) => {
        editor.chain().focus().setWordArt(style.id).run();
      },
    });
  });

  // Add table (only for full variant)
  items.push({
    title: 'Table',
    description: 'Insert a table',
    icon: '⊞',
    keywords: ['table', 'grid', 'spreadsheet'],
    command: (editor) => {
      editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
    },
  });

  return items;
};

// Slash command extension
const SlashCommand = Suggestion.configure({
  suggestion: {
    char: '/',
    startOfLine: false,
    command: ({ editor, range, props }: any) => {
      props.command({ editor, range });
    },
    items: ({ query, editor }: { query: string; editor: Editor }) => {
      const items = getMenuItems(editor);
      if (!query) return items;

      const lowerQuery = query.toLowerCase();
      return items.filter((item) => {
        const searchString = `${item.title} ${item.description} ${item.keywords?.join(' ')}`.toLowerCase();
        return searchString.includes(lowerQuery);
      });
    },
    render: () => {
      let component: ReactRenderer<any>;
      let popup: TippyInstance[];

      return {
        onStart: (props: any) => {
          component = new ReactRenderer(SlashCommandMenu, {
            props: {
              ...props,
              items: getMenuItems(props.editor).map((item) => ({
                ...item,
                command: () => {
                  item.command(props.editor);
                  props.editor.chain().focus().deleteRange(props.range).run();
                },
              })),
            },
            editor: props.editor,
          });

          if (!props.clientRect) {
            return;
          }

          popup = tippy('body', {
            getReferenceClientRect: props.clientRect,
            appendTo: () => document.body,
            content: component.element,
            showOnCreate: true,
            interactive: true,
            trigger: 'manual',
            placement: 'bottom-start',
          });
        },

        onUpdate(props: any) {
          component.updateProps({
            ...props,
            items: getMenuItems(props.editor).map((item) => ({
              ...item,
              command: () => {
                item.command(props.editor);
                props.editor.chain().focus().deleteRange(props.range).run();
              },
            })),
          });

          if (!props.clientRect) {
            return;
          }

          popup[0].setProps({
            getReferenceClientRect: props.clientRect,
          });
        },

        onKeyDown(props: any) {
          if (props.event.key === 'Escape') {
            popup[0].hide();
            return true;
          }

          return component.ref?.onKeyDown(props);
        },

        onExit() {
          popup[0].destroy();
          component.destroy();
        },
      };
    },
  },
});

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  content = '',
  onChange,
  placeholder = 'Type / for commands, * for bullets, - for lists...',
  variant = 'minimal',
  className = '',
  autoFocus = false,
}) => {
  const extensions = [
    StarterKit.configure({
      codeBlock: false, // We'll use CodeBlockLowlight instead
    }),
    Placeholder.configure({
      placeholder,
    }),
    SlashCommand,
    WordArt,
  ];

  // Add table extensions only for full variant
  if (variant === 'full') {
    extensions.push(
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      CodeBlockLowlight.configure({
        lowlight,
      })
    );
  } else {
    // Still allow code blocks in minimal, just simpler
    extensions.push(
      CodeBlockLowlight.configure({
        lowlight,
      })
    );
  }

  const editor = useEditor({
    extensions,
    content,
    editorProps: {
      attributes: {
        class: 'focus:outline-none',
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      onChange?.(html);
    },
    autofocus: autoFocus,
  });

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  return (
    <div className={`rich-text-editor ${variant === 'full' ? 'full-featured' : 'minimal'} ${className}`}>
      <EditorContent editor={editor} />
    </div>
  );
};

export default RichTextEditor;
