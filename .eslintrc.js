module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'svelte'],
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    '@typescript-eslint/recommended-requiring-type-checking',
    'prettier'
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    tsconfigRootDir: __dirname,
    project: ['./tsconfig.json', './apps/*/tsconfig.json', './packages/*/tsconfig.json'],
    extraFileExtensions: ['.svelte']
  },
  env: {
    browser: true,
    es2022: true,
    node: true
  },
  overrides: [
    {
      files: ['*.svelte'],
      processor: 'svelte/svelte',
      parser: 'svelte-eslint-parser',
      parserOptions: {
        parser: '@typescript-eslint/parser'
      },
      extends: ['plugin:svelte/recommended']
    },
    {
      files: ['apps/api/**/*.ts'],
      env: {
        node: true,
        browser: false
      }
    },
    {
      files: ['apps/web/**/*.ts', 'apps/web/**/*.svelte'],
      env: {
        browser: true,
        node: false
      }
    }
  ],
  rules: {
    // Prevent duplicate exports and declarations
    '@typescript-eslint/no-duplicate-imports': 'error',
    'no-duplicate-imports': 'off', // Use TypeScript version instead
    'no-redeclare': 'error',
    '@typescript-eslint/no-redeclare': 'error',
    
    // Prevent naming conflicts
    '@typescript-eslint/no-shadow': 'error',
    'no-shadow': 'off', // Use TypeScript version instead
    
    // Ensure imports are used
    '@typescript-eslint/no-unused-vars': ['error', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      ignoreRestSiblings: true
    }],
    
    // Type safety
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unsafe-assignment': 'warn',
    '@typescript-eslint/no-unsafe-member-access': 'warn',
    '@typescript-eslint/no-unsafe-call': 'warn',
    '@typescript-eslint/no-unsafe-return': 'warn',
    '@typescript-eslint/restrict-template-expressions': 'warn',
    
    // Code quality
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error',
    '@typescript-eslint/no-unnecessary-condition': 'warn',
    '@typescript-eslint/strict-boolean-expressions': 'warn',
    
    // Function and variable declarations
    'prefer-const': 'error',
    'no-var': 'error',
    
    // Prevent common mistakes
    'no-implicit-coercion': 'error',
    'no-implicit-globals': 'error',
    'no-undef': 'error',
    
    // Database/ORM specific rules
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    
    // Svelte-specific rules
    'svelte/no-duplicate-style-properties': 'error',
    'svelte/no-unused-svelte-ignore': 'error',
    'svelte/valid-compile': 'error'
  },
  ignorePatterns: [
    'dist/',
    'build/',
    'node_modules/',
    '.svelte-kit/',
    'migrations/',
    '*.config.js',
    '*.config.ts'
  ]
};