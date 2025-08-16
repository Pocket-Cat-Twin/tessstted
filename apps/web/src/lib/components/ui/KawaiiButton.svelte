<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'outline' | 'gothic' | 'white' = 'gothic';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let href: string | undefined = undefined;
  export let disabled = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let className = '';

  const variants = {
    primary: 'btn-gothic',
    secondary: 'glass border border-gothic-light text-gothic-white hover:border-gothic-accent hover:bg-gothic-accent-light',
    outline: 'glass border border-gothic-accent text-gothic-accent hover:bg-gothic-accent-light hover:text-gothic-white',
    gothic: 'btn-gothic',
    white: 'btn-white'
  };

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg'
  };

  $: classes = `
    inline-flex items-center justify-center font-medium rounded-lg transition-all duration-300
    focus:outline-none focus-visible hover-lift
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    ${variants[variant]}
    ${variant !== 'gothic' && variant !== 'white' ? sizes[size] : ''}
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