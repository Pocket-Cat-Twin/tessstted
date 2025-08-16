module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'svelte'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier'
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
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
    'no-duplicate-imports': 'error',
    'no-redeclare': 'error',
    
    // Prevent naming conflicts
    '@typescript-eslint/no-shadow': 'error',
    'no-shadow': 'off',
    
    // Ensure imports are used
    '@typescript-eslint/no-unused-vars': ['error', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      ignoreRestSiblings: true
    }],
    
    // Type safety
    '@typescript-eslint/no-explicit-any': 'warn',
    
    // Function and variable declarations
    'prefer-const': 'error',
    'no-var': 'error',
    
    // Prevent common mistakes
    'no-implicit-coercion': 'error',
    'no-implicit-globals': 'error',
    'no-undef': 'error',
    
    // Database/ORM specific rules
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    
    // Svelte-specific rules - simplified
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