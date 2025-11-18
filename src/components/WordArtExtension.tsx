import { Node, mergeAttributes } from '@tiptap/core';

export interface WordArtOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    wordArt: {
      setWordArt: (style: string) => ReturnType;
      toggleWordArt: (style: string) => ReturnType;
    };
  }
}

export const WordArt = Node.create<WordArtOptions>({
  name: 'wordArt',

  group: 'block',

  content: 'inline*',

  defining: true,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      style: {
        default: 'gradient-blue',
        parseHTML: element => element.getAttribute('data-style'),
        renderHTML: attributes => {
          return {
            'data-style': attributes.style,
            class: `word-art word-art-${attributes.style}`,
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-style]',
        getAttrs: node => {
          const element = node as HTMLElement;
          return element.hasAttribute('data-style') && null;
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0];
  },

  addCommands() {
    return {
      setWordArt:
        (style: string) =>
        ({ commands }) => {
          return commands.setNode(this.name, { style });
        },
      toggleWordArt:
        (style: string) =>
        ({ commands }) => {
          return commands.toggleNode(this.name, 'paragraph', { style });
        },
    };
  },
});

// Word Art styles definitions
export const WORD_ART_STYLES = [
  {
    id: 'gradient-blue',
    name: 'Ocean Wave',
    preview: '🌊',
  },
  {
    id: 'gradient-rainbow',
    name: 'Rainbow',
    preview: '🌈',
  },
  {
    id: 'gradient-fire',
    name: 'Fire',
    preview: '🔥',
  },
  {
    id: 'gradient-gold',
    name: 'Golden',
    preview: '✨',
  },
  {
    id: 'shadow-3d',
    name: '3D Shadow',
    preview: '📦',
  },
  {
    id: 'neon-glow',
    name: 'Neon Glow',
    preview: '💡',
  },
  {
    id: 'retro-wave',
    name: 'Retro Wave',
    preview: '🌅',
  },
  {
    id: 'chrome',
    name: 'Chrome',
    preview: '🪞',
  },
];
