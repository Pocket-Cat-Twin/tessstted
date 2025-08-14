<script lang="ts">
  export let className = '';
  export let variant: 'default' | 'pink' | 'lavender' | 'peach' | 'mint' = 'default';
  export let withFlowers = false;
  export let href: string | undefined = undefined;

  const variants = {
    default: 'from-kawaii-cream to-white border-kawaii-pink/30',
    pink: 'from-kawaii-pink to-white border-kawaii-pink/50',
    lavender: 'from-kawaii-lavender to-white border-kawaii-lavender/50',
    peach: 'from-kawaii-peach to-white border-kawaii-peach/50',
    mint: 'from-kawaii-mint to-white border-kawaii-mint/50'
  };

  $: cardClasses = `
    card-kawaii bg-gradient-to-br ${variants[variant]}
    ${withFlowers ? 'cherry-blossoms' : ''}
    ${className}
  `.trim();
</script>

{#if href}
  <a {href} class="{cardClasses} block p-6 hover:scale-105 transition-transform duration-200">
    <slot />
  </a>
{:else}
  <div class="{cardClasses} p-6">
    <slot />
  </div>
{/if}