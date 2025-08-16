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

  // Gothic base button styles
  const baseClasses = 'inline-flex items-center justify-center font-medium transition-all duration-300 focus:outline-none focus-visible position-relative overflow-hidden';
  
  // Gothic variant styles
  const variantClasses = {
    primary: 'btn-gothic',
    secondary: 'btn-white',
    outline: 'glass border border-gothic-light text-gothic-white hover:border-gothic-accent hover:bg-gothic-accent-light rounded-lg',
    ghost: 'text-gothic-secondary hover:text-gothic-white hover:bg-gothic-accent-light rounded-lg',
    danger: 'glass border border-red-500 text-red-400 hover:border-red-400 hover:bg-red-500/10 rounded-lg'
  };
  
  // Gothic size styles
  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg'
  };

  $: buttonClasses = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    fullWidth && 'w-full',
    disabled && 'opacity-50 cursor-not-allowed',
    loading && 'relative',
    className
  ].filter(Boolean).join(' ');
</script>

{#if href}
  <a {href} class={buttonClasses} class:pointer-events-none={disabled || loading}>
    {#if loading}
      <div class="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
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
      <div class="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
    {/if}
    <slot />
  </button>
{/if}

