<script lang="ts">
  import { onMount } from 'svelte';
  import { authStore } from '$stores/auth';
  import { configStore } from '$stores/config';
  import Header from '$lib/components/layout/Header.svelte';
  import Footer from '$lib/components/layout/Footer.svelte';
  import '../app.css';

  // Accept SvelteKit props to prevent warnings
  export let data: any = undefined;

  // Импорт диагностики API в development режиме
  import '$lib/utils/api-diagnostics';

  onMount(() => {
    console.log('🏠 Layout MOUNTING');
    console.log('🏠 Current authStore state on mount:', $authStore);
    
    // Initialize stores
    console.log('🔄 Starting authStore initialization...');
    authStore.init();
    
    console.log('🔄 Starting configStore initialization...');
    configStore.init();
    
    console.log('✅ Layout store initialization calls completed');
  });

  // Add reactive logging to track auth state changes
  $: {
    console.log('🔄 Auth state changed:', {
      hasUser: !!$authStore.user,
      loading: $authStore.loading,
      initialized: $authStore.initialized,
      userEmail: $authStore.user?.email
    });
  }
</script>

<!-- Отдельный белый фон -->
<div class="gothic-white-background"></div>

<!-- Глобальный hero градиент -->
<div class="global-hero-gradient"></div>

<!-- Градиент от хэдера -->
<div class="header-gradient"></div>

<div class="min-h-screen flex flex-col gothic-pattern-background">
  <Header />
  
  <main class="flex-1 relative">
    <slot />
  </main>
  
  <div class="relative">
    <!-- Градиент к футеру -->
    <div class="footer-gradient"></div>
    <Footer />
  </div>
</div>