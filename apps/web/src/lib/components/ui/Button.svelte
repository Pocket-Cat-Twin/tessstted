<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let loading = false;
  export let disabled = false;
  export let href: string | undefined = undefined;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let fullWidth = false;
  
  // Accept custom class prop
  let className = '';
  export { className as class };

  $: buttonClasses = [
    'btn',
    `btn-${variant}`,
    `btn-${size}`,
    fullWidth && 'w-full',
    disabled && 'opacity-50 cursor-not-allowed',
    loading && 'relative',
    className
  ].filter(Boolean).join(' ');
</script>

{#if href}
  <a {href} class={buttonClasses} class:pointer-events-none={disabled || loading}>
    {#if loading}
      <div class="spinner w-4 h-4 mr-2"></div>
    {/if}
    <slot />
  </a>
{:else}
  <button 
    {type} 
    {disabled} 
    class={buttonClasses}
    on:click
  >
    {#if loading}
      <div class="spinner w-4 h-4 mr-2"></div>
    {/if}
    <slot />
  </button>
{/if}

<style>
  .btn {
    @apply inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2;
  }
  
  .btn-primary {
    @apply bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500;
  }
  
  .btn-secondary {
    @apply bg-secondary-100 text-secondary-900 hover:bg-secondary-200 focus:ring-secondary-500;
  }
  
  .btn-outline {
    @apply border border-primary-600 text-primary-600 bg-white hover:bg-primary-50 focus:ring-primary-500;
  }
  
  .btn-ghost {
    @apply text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:ring-gray-500;
  }
  
  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
  }
  
  .btn-sm {
    @apply px-3 py-1.5 text-sm;
  }
  
  .btn-md {
    @apply px-4 py-2 text-base;
  }
  
  .btn-lg {
    @apply px-6 py-3 text-lg;
  }

  .spinner {
    @apply border-2 border-current border-t-transparent rounded-full animate-spin;
  }
</style>