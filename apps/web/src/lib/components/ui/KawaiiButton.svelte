<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'outline' | 'kawaii' | 'white' = 'kawaii';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let href: string | undefined = undefined;
  export let disabled = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let className = '';

  const variants = {
    primary: 'bg-primary-500 text-white hover:bg-primary-600',
    secondary: 'bg-secondary-100 text-secondary-900 hover:bg-secondary-200',
    outline: 'border border-primary-500 text-primary-500 hover:bg-primary-50',
    kawaii: 'btn-kawaii',
    white: 'btn-white'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  $: classes = `
    inline-flex items-center justify-center font-medium rounded-full transition-all duration-200
    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    ${variants[variant]}
    ${variant !== 'kawaii' && variant !== 'white' ? sizes[size] : ''}
    ${className}
  `.trim();
</script>

{#if href && !disabled}
  <a {href} class={classes} role="button">
    <slot />
  </a>
{:else}
  <button
    {type}
    {disabled}
    class={classes}
    on:click
    on:keydown
  >
    <slot />
  </button>
{/if}