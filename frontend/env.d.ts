/// <reference types="vite/client" />
interface Window {
    MathJax?: {
        typesetPromise?: () => Promise<void>;
    };
}
declare const MathJax: Window['MathJax'];
