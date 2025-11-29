import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import type { Components } from 'react-markdown';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const markdownComponents: Components = {
  a: ({ ...props }) => (
    <a
      {...props}
      className="text-blue-600 hover:text-blue-800 underline"
      target="_blank"
      rel="noopener noreferrer"
    />
  ),
  code(props) {
    const { inline, className, children, ...rest } = props as {
      inline?: boolean;
      className?: string;
      children?: React.ReactNode;
      [key: string]: unknown;
    };
    if (inline) {
      return (
        <code
          className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono"
          {...props}
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className={`${className || ''} block bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto`}
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ ...props }) => (
    <pre
      className="bg-gray-100 p-2 rounded overflow-x-auto text-xs"
      {...props}
    />
  ),
  p: ({ ...props }) => (
    <p className="mb-2 last:mb-0" {...props} />
  ),
  ul: ({ ...props }) => (
    <ul className="list-disc list-inside mb-2 space-y-1" {...props} />
  ),
  ol: ({ ...props }) => (
    <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />
  ),
  blockquote: ({ ...props }) => (
    <blockquote
      className="border-l-4 border-gray-300 pl-4 italic text-gray-600 my-2"
      {...props}
    />
  ),
  table: ({ ...props }) => (
    <div className="my-4 w-full overflow-y-hidden overflow-x-auto block">
      <table className="w-full divide-y divide-gray-300 border border-gray-300" {...props} />
    </div>
  ),
  thead: ({ ...props }) => (
    <thead className="bg-gray-100" {...props} />
  ),
  tbody: ({ ...props }) => (
    <tbody className="divide-y divide-gray-200 bg-white" {...props} />
  ),
  tr: ({ ...props }) => (
    <tr className="hover:bg-gray-50" {...props} />
  ),
  th: ({ ...props }) => (
    <th
      className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 border-b border-gray-300"
      {...props}
    />
  ),
  td: ({ ...props }) => (
    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500 border-b border-gray-300" {...props} />
  ),
};

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm max-w-none break-words ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;
