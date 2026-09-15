/// <reference types="vite/client" />

// Allow plain CSS imports in TypeScript
declare module '*.css' {
  const content: Record<string, string>
  export default content
}
