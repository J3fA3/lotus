import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useEditor, EditorContent, Editor, Extension } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { CodeBlockLowlight } from '@tiptap/extension-code-block-lowlight';
import { Placeholder } from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import { common, createLowlight } from 'lowlight';
import { ReactRenderer } from '@tiptap/react';
import tippy, { Instance as TippyInstance } from 'tippy.js';
import Suggestion from '@tiptap/suggestion';
import { InputRule } from '@tiptap/core';

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
      title: 'Task List',
      description: 'Interactive checklist with checkboxes',
      icon: '☑',
      keywords: ['task', 'todo', 'checkbox', 'checklist', 'check', 'done'],
      command: ({ editor, range }) => {
        editor
          .chain()
          .focus()
          .deleteRange(range)
          .toggleTaskList()
          .run();
      },
    },
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
  // Track if we're currently updating from user input to prevent feedback loops
  const isLocalUpdateRef = useRef(false);
  const previousContentRef = useRef(content);
  const resetLocalUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const extensions = [
    StarterKit.configure({
      codeBlock: false, // We'll use CodeBlockLowlight instead
    }),
    Placeholder.configure({
      placeholder,
    }),
    // Task list with interactive checkboxes
    TaskList.configure({
      HTMLAttributes: {
        class: 'task-list',
      },
    }),
    TaskItem.configure({
      nested: true, // Allow nested task items
      HTMLAttributes: {
        class: 'task-item',
      },
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
    // Custom keyboard shortcuts and input rules extension
    Extension.create({
      name: 'customKeyboardShortcuts',
      addKeyboardShortcuts() {
        return {
          // Cmd+> or Ctrl+> for blockquote (Slack-style)
          'Mod->': () => this.editor.commands.toggleBlockquote(),
          
          // Tab to indent list items (sink into nested list)
          'Tab': () => {
            if (this.editor.isActive('listItem') || this.editor.isActive('taskItem')) {
              return this.editor.commands.sinkListItem('listItem') || 
                     this.editor.commands.sinkListItem('taskItem');
            }
            return false;
          },
          
          // Shift+Tab to outdent list items (lift from nested list)
          'Shift-Tab': () => {
            if (this.editor.isActive('listItem') || this.editor.isActive('taskItem')) {
              return this.editor.commands.liftListItem('listItem') ||
                     this.editor.commands.liftListItem('taskItem');
            }
            return false;
          },
          
          // Backspace at empty list item exits the list
          'Backspace': () => {
            const { state } = this.editor;
            const { $from } = state.selection;
            
            // Check if we're at the start of a list item and it's empty
            if (this.editor.isActive('listItem') || this.editor.isActive('taskItem')) {
              const node = $from.node($from.depth);
              const isEmptyNode = node.textContent === '';
              const isAtStart = $from.parentOffset === 0;
              
              if (isEmptyNode && isAtStart) {
                // Try to lift/exit the list
                if (this.editor.isActive('taskItem')) {
                  return this.editor.commands.liftListItem('taskItem');
                }
                return this.editor.commands.liftListItem('listItem');
              }
            }
            return false;
          },
        };
      },
      addInputRules() {
        // Input rule for unchecked task: [ ] at start of line
        const uncheckedTaskRule = new InputRule({
          find: /^\s*\[\s?\]\s$/,
          handler: ({ state, range, chain }) => {
            chain()
              .deleteRange(range)
              .toggleTaskList()
              .run();
          },
        });
        
        // Input rule for checked task: [x] or [X] at start of line
        const checkedTaskRule = new InputRule({
          find: /^\s*\[[xX]\]\s$/,
          handler: ({ state, range, chain }) => {
            chain()
              .deleteRange(range)
              .toggleTaskList()
              .updateAttributes('taskItem', { checked: true })
              .run();
          },
        });
        
        return [uncheckedTaskRule, checkedTaskRule];
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
      // Mark that this is a local update from user typing
      isLocalUpdateRef.current = true;

      // Clear any existing timeout
      if (resetLocalUpdateTimeoutRef.current) {
        clearTimeout(resetLocalUpdateTimeoutRef.current);
      }

      // Set a timeout to allow external updates again after user stops typing
      // This prevents immediate overwrites from stale props while typing
      resetLocalUpdateTimeoutRef.current = setTimeout(() => {
        isLocalUpdateRef.current = false;
      }, 2000);

      previousContentRef.current = html;
      onChange?.(html);
    },
    autofocus: autoFocus,
  });

  // Only sync content when it's an external change (not from user typing)
  // Only sync content when it's an external change (not from user typing)
  useEffect(() => {
    if (!editor) return;

    // If this is a local update (from user typing), don't sync
    if (isLocalUpdateRef.current) {
      return;
    }

    // Only update if content actually changed from an external source
    const currentContent = editor.getHTML();
    if (content !== currentContent && content !== previousContentRef.current) {
      previousContentRef.current = content;
      // Save cursor position
      const { from, to } = editor.state.selection;

      editor.commands.setContent(content, { emitUpdate: false }); // false = don't emit update event

      // Restore cursor position if possible (best effort)
      // Note: This is tricky because the content length might have changed
      // But for minor updates it helps keep context
      try {
        const newDocSize = editor.state.doc.content.size;
        if (from <= newDocSize && to <= newDocSize) {
          editor.commands.setTextSelection({ from, to });
        }
      } catch (e) {
        // Ignore selection errors
      }
    }
  }, [content, editor]);

  const variantClass = variant === 'full' ? 'full-featured' : variant === 'title' ? 'title' : 'minimal';
  const [showTableMenu, setShowTableMenu] = useState(false);

  // Check if we're in a table - optimized to only update when actually changes
  useEffect(() => {
    if (!editor) return;

    const updateTableState = () => {
      const isInTable = editor.isActive('table');
      // Only update state if it actually changed
      setShowTableMenu(prev => {
        if (prev !== isInTable) {
          return isInTable;
        }
        return prev;
      });
    };

    // Only listen to selection updates (less frequent than transaction)
    editor.on('selectionUpdate', updateTableState);

    return () => {
      editor.off('selectionUpdate', updateTableState);
      if (resetLocalUpdateTimeoutRef.current) {
        clearTimeout(resetLocalUpdateTimeoutRef.current);
      }
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
