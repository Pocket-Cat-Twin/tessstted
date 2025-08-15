<script lang="ts">
  import { onMount } from 'svelte';
  import { authStore } from '$stores/auth';
  import { configStore } from '$stores/config';
  import Header from '$lib/components/layout/Header.svelte';
  import Footer from '$lib/components/layout/Footer.svelte';
  import '../app.css';

  onMount(() => {
    // Initialize stores
    authStore.init();
    configStore.init();
  });
</script>

<div class="min-h-screen flex flex-col floral-bg">
  <Header />
  
  <main class="flex-1 relative">
    <slot />
  </main>
  
  <Footer />
</div>