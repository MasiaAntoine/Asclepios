/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

declare module '*.md?raw' {
  const content: string
  export default content
}

declare module '*.md' {
  const content: string
  export default content
}

declare module '*.json?raw' {
  const content: string
  export default content
}

declare module '*.csv?raw' {
  const content: string
  export default content
}
