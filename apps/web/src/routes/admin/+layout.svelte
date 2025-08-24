<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { authStore } from '$lib/stores/auth';
  import AdminSidebar from '$lib/components/admin/AdminSidebar.svelte';
  import Button from '$lib/components/ui/Button.svelte';

  $: user = $authStore.user;

  // Check if user is admin
  onMount(() => {
    if ($authStore.initialized && (!user || user.role !== 'admin')) {
      goto('/');
    }
  });

  // Handle logout
  async function handleLogout() {
    await authStore.logout();
    goto('/');
  }
</script>

<svelte:head>
  <title>Админ панель - YuYu Lolita Shopping</title>
</svelte:head>

<!-- Check if user is admin -->
{#if user && user.role === 'admin'}
  <div class="flex h-screen bg-gray-100">
    <!-- Sidebar -->
    <div class="w-64 flex-shrink-0">
      <AdminSidebar />
    </div>

    <!-- Main content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top bar -->
      <header class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-xl font-semibold text-gray-900">
              Панель администратора
            </h1>
            <p class="text-sm text-gray-600">
              Управление системой YuYu Lolita Shopping
            </p>
          </div>

          <div class="flex items-center space-x-4">
            <!-- Quick actions -->
            <Button variant="outline" size="sm" href="/">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              На сайт
            </Button>

            <!-- User menu -->
            <div class="flex items-center space-x-3">
              <div class="flex items-center space-x-2">
                <div class="w-8 h-8 bg-pink-500 rounded-full flex items-center justify-center">
                  <span class="text-white font-medium text-sm">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div class="text-sm">
                  <div class="font-medium text-gray-900">{user.name}</div>
                  <div class="text-gray-500">Администратор</div>
                </div>
              </div>

              <Button variant="ghost" size="sm" on:click={handleLogout}>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto">
        <slot />
      </main>
    </div>
  </div>
{:else}
  <!-- Loading or unauthorized -->
  <div class="min-h-screen bg-gray-100 flex items-center justify-center">
    <div class="text-center">
      <div class="w-16 h-16 bg-gray-300 rounded-full animate-pulse mx-auto mb-4"></div>
      <p class="text-gray-600">Проверка доступа...</p>
    </div>
  </div>
{/if}