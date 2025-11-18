import React, { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import { Editor } from '@tiptap/react';

export interface MenuItem {
  title: string;
  description: string;
  icon: string;
  command: (editor: Editor) => void;
  keywords?: string[];
}

export interface MenuProps {
  items: MenuItem[];
  command: (item: MenuItem) => void;
  editor: Editor;
  range: any;
}

export const SlashCommandMenu = forwardRef<any, MenuProps>((props, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filteredItems, setFilteredItems] = useState(props.items);
  const [query, setQuery] = useState('');
  const selectedItemRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setFilteredItems(props.items);
    setSelectedIndex(0);
  }, [props.items]);

  // Auto-scroll selected item into view
  useEffect(() => {
    if (selectedItemRef.current && menuRef.current) {
      const menuRect = menuRef.current.getBoundingClientRect();
      const itemRect = selectedItemRef.current.getBoundingClientRect();

      const isAbove = itemRect.top < menuRect.top;
      const isBelow = itemRect.bottom > menuRect.bottom;

      if (isAbove || isBelow) {
        selectedItemRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      }
    }
  }, [selectedIndex]);

  const selectItem = (index: number) => {
    const item = filteredItems[index];
    if (item) {
      props.command(item);
    }
  };

  const upHandler = () => {
    setSelectedIndex((selectedIndex + filteredItems.length - 1) % filteredItems.length);
  };

  const downHandler = () => {
    setSelectedIndex((selectedIndex + 1) % filteredItems.length);
  };

  const enterHandler = () => {
    selectItem(selectedIndex);
  };

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === 'ArrowUp') {
        upHandler();
        return true;
      }

      if (event.key === 'ArrowDown') {
        downHandler();
        return true;
      }

      if (event.key === 'Enter') {
        enterHandler();
        return true;
      }

      // Handle filtering based on typing
      if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
        const newQuery = query + event.key;
        setQuery(newQuery);
        const filtered = props.items.filter(item => {
          const searchString = `${item.title} ${item.description} ${item.keywords?.join(' ')}`.toLowerCase();
          return searchString.includes(newQuery.toLowerCase());
        });
        setFilteredItems(filtered);
        setSelectedIndex(0);
        return false; // Let the character be typed
      }

      if (event.key === 'Backspace' && query.length > 0) {
        const newQuery = query.slice(0, -1);
        setQuery(newQuery);
        if (newQuery === '') {
          setFilteredItems(props.items);
        } else {
          const filtered = props.items.filter(item => {
            const searchString = `${item.title} ${item.description} ${item.keywords?.join(' ')}`.toLowerCase();
            return searchString.includes(newQuery.toLowerCase());
          });
          setFilteredItems(filtered);
        }
        setSelectedIndex(0);
        return false;
      }

      return false;
    },
  }));

  if (filteredItems.length === 0) {
    return (
      <div className="slash-menu-wrapper">
        <div className="slash-menu">
          <div className="slash-menu-item opacity-50">
            No results found
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="slash-menu-wrapper">
      <div className="slash-menu" ref={menuRef}>
        {query && (
          <div className="slash-menu-query">
            Searching: <span className="font-semibold">{query}</span>
          </div>
        )}
        {filteredItems.map((item, index) => (
          <button
            ref={index === selectedIndex ? selectedItemRef : null}
            className={`slash-menu-item ${index === selectedIndex ? 'is-selected' : ''}`}
            key={index}
            onClick={() => selectItem(index)}
            type="button"
          >
            <div className="slash-menu-item-icon">{item.icon}</div>
            <div className="slash-menu-item-content">
              <div className="slash-menu-item-title">{item.title}</div>
              <div className="slash-menu-item-description">{item.description}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
});

SlashCommandMenu.displayName = 'SlashCommandMenu';
