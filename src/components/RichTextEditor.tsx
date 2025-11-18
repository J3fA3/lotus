import React, { useEffect, useState } from 'react';
import { useEditor, EditorContent, Editor, Extension } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { CodeBlockLowlight } from '@tiptap/extension-code-block-lowlight';
import { Placeholder } from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import { common, createLowlight } from 'lowlight';
import { ReactRenderer } from '@tiptap/react';
import tippy, { Instance as TippyInstance } from 'tippy.js';
import Suggestion from '@tiptap/suggestion';

import { SlashCommandMenu, MenuItem } from './RichTextEditorMenu';
import { WordArt, WORD_ART_STYLES } from './WordArtExtension';
import { TableMenu } from './TableMenu';
import './rich-text-editor.css';

const lowlight = createLowlight(common);

interface RichTextEditorProps {
  content?: string;
  onChange?: (content: string) => void;
  placeholder?: string;
  variant?: 'minimal' | 'full' | 'title';
  className?: string;
  autoFocus?: boolean;
}

// Slash command configuration
const getMenuItems = (editor: Editor, variant?: string): MenuItem[] => {
  const items: MenuItem[] = [];

  // For title variant, only show Word Art
  if (variant === 'title') {
    WORD_ART_STYLES.forEach((style) => {
      items.push({
        title: `Word Art: ${style.name}`,
        description: 'Retro-styled text formatting',
        icon: style.preview,
        keywords: ['wordart', 'word', 'art', 'style', 'retro', style.name.toLowerCase()],
        command: ({ editor, range }) => {
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .setWordArt(style.id)
            .run();
        },
      });
    });

    // Add plain text option
    items.unshift({
      title: 'Plain Text',
      description: 'Remove Word Art styling',
      icon: 'T',
      keywords: ['plain', 'text', 'normal', 'remove', 'clear'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setParagraph()
          .run();
      },
    });

    return items;
  }

  // For other variants, show all formatting options
  // Headings
  items.push(
    {
      title: 'Heading 1',
      description: 'Large section heading',
      icon: 'H1',
      keywords: ['h1', 'heading', 'title', 'large'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setHeading({ level: 1 })
          .run();
      },
    },
    {
      title: 'Heading 2',
      description: 'Medium section heading',
      icon: 'H2',
      keywords: ['h2', 'heading', 'subtitle', 'medium'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setHeading({ level: 2 })
          .run();
      },
    },
    {
      title: 'Heading 3',
      description: 'Small section heading',
      icon: 'H3',
      keywords: ['h3', 'heading', 'small'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setHeading({ level: 3 })
          .run();
      },
    },

    // Lists
    {
      title: 'Bullet List',
      description: 'Create a bullet point list',
      icon: '•',
      keywords: ['bullet', 'list', 'ul', 'unordered'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleBulletList()
          .run();
      },
    },
    {
      title: 'Numbered List',
      description: 'Create a numbered list',
      icon: '1.',
      keywords: ['number', 'list', 'ol', 'ordered'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleOrderedList()
          .run();
      },
    },

    // Code
    {
      title: 'Code Block',
      description: 'Insert a code block with syntax highlighting',
      icon: '</>',
      keywords: ['code', 'block', 'programming', 'syntax'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleCodeBlock()
          .run();
      },
    },

    // Quote
    {
      title: 'Quote',
      description: 'Insert a blockquote',
      icon: '"',
      keywords: ['quote', 'blockquote', 'citation'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleBlockquote()
          .run();
      },
    },

    // Divider
    {
      title: 'Divider',
      description: 'Insert a horizontal line',
      icon: '—',
      keywords: ['divider', 'line', 'hr', 'separator'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setHorizontalRule()
          .run();
      },
    }
  );

  // Add Word Art styles (fun feature!)
  WORD_ART_STYLES.forEach((style) => {
    items.push({
      title: `Word Art: ${style.name}`,
      description: 'Retro-styled text formatting',
      icon: style.preview,
      keywords: ['wordart', 'word', 'art', 'style', 'retro', style.name.toLowerCase()],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .setWordArt(style.id)
          .run();
      },
    });
  });

  // Add table (only for full variant)
  if (variant === 'full') {
    items.push({
      title: 'Table',
      description: 'Insert a table',
      icon: '⊞',
      keywords: ['table', 'grid', 'spreadsheet'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
          .run();
      },
    });
  }

  return items;
};

// Slash command extension factory
const createSlashCommand = (variant?: string) => Extension.create({
  name: 'slashCommand',

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: '/',
        startOfLine: false,
        command: ({ editor, range, props }: any) => {
          // props is the selected menu item
          // Execute the item's command with editor and range
          props.command({ editor, range });
        },
        items: ({ query, editor }: { query: string; editor: Editor }) => {
          const items = getMenuItems(editor, variant);
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
                  items: getMenuItems(props.editor, variant),
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
                items: getMenuItems(props.editor, variant),
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
      }),
    ];
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
    // Link extension with autolink and custom paste handler
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        class: 'text-blue-600 underline hover:text-blue-800',
      },
    }),
    createSlashCommand(variant),
    WordArt,
    // Custom keyboard shortcuts extension
    Extension.create({
      name: 'customKeyboardShortcuts',
      addKeyboardShortcuts() {
        return {
          // Cmd+> or Ctrl+> for blockquote (Slack-style)
          'Mod->': () => this.editor.commands.toggleBlockquote(),
        };
      },
    }),
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
  } else if (variant === 'minimal') {
    // Still allow code blocks in minimal, just simpler
    extensions.push(
      CodeBlockLowlight.configure({
        lowlight,
      })
    );
  }
  // For title variant, we don't need code blocks or links

  const editor = useEditor({
    extensions,
    content,
    editorProps: {
      attributes: {
        class: 'focus:outline-none',
      },
      // Custom paste handler for Slack-style paste-link-over-selection
      handlePaste: (view, event) => {
        const text = event.clipboardData?.getData('text/plain');

        // Check if pasted text is a URL
        const isUrl = text && (
          text.startsWith('http://') ||
          text.startsWith('https://') ||
          text.startsWith('www.')
        );

        // Get current selection
        const { from, to } = view.state.selection;
        const hasSelection = from !== to;

        // If we have selected text and pasting a URL, create a link
        if (isUrl && hasSelection) {
          const { state } = view;
          const selectedText = state.doc.textBetween(from, to);

          // Use the editor to set the link
          if (editor) {
            editor
              .chain()
              .focus()
              .setLink({ href: text })
              .run();

            return true; // Prevent default paste behavior
          }
        }

        return false; // Use default paste behavior
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

  const variantClass = variant === 'full' ? 'full-featured' : variant === 'title' ? 'title' : 'minimal';
  const [showTableMenu, setShowTableMenu] = useState(false);

  // Check if we're in a table
  useEffect(() => {
    if (!editor) return;

    const updateTableState = () => {
      setShowTableMenu(editor.isActive('table'));
    };

    editor.on('selectionUpdate', updateTableState);
    editor.on('transaction', updateTableState);

    return () => {
      editor.off('selectionUpdate', updateTableState);
      editor.off('transaction', updateTableState);
    };
  }, [editor]);

  return (
    <div className={`rich-text-editor ${variantClass} ${className}`}>
      {editor && variant === 'full' && showTableMenu && (
        <div className="mb-2">
          <TableMenu editor={editor} />
        </div>
      )}
      <EditorContent editor={editor} />
    </div>
  );
};

export default RichTextEditor;
