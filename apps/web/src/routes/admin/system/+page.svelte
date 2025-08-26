<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Badge from '$lib/components/ui/Badge.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';

  let backupStatus: any = null;
  let cleanupStats: any = null;
  let loading = true;
  let actionLoading = '';
  let showConfirmModal = false;
  let confirmAction: any = null;

  onMount(() => {
    loadSystemData();
  });

  async function loadSystemData() {
    loading = true;
    try {
      const [backupResponse, cleanupResponse] = await Promise.all([
        fetch('/backup/status'),
        fetch('/cleanup/statistics')
      ]);

      const [backupData, cleanupData] = await Promise.all([
        backupResponse.json(),
        cleanupResponse.json()
      ]);

      if (backupData.success) {
        backupStatus = backupData.data;
      }

      if (cleanupData.success) {
        cleanupStats = cleanupData.data;
      }

    } catch (error) {
      console.error('Failed to load system data:', error);
    } finally {
      loading = false;
    }
  }

  async function createBackup(type: string) {
    actionLoading = `backup-${type}`;
    try {
      const response = await fetch(`/backup/create/${type}`, {
        method: 'POST'
      });
      const result = await response.json();
      
      if (result.success) {
        alert(`Backup created successfully: ${result.data.fileName}`);
        await loadSystemData();
      } else {
        alert(`Backup failed: ${result.message}`);
      }
    } catch (error) {
      alert('Network error during backup');
    } finally {
      actionLoading = '';
    }
  }

  async function runCleanup() {
    actionLoading = 'cleanup';
    try {
      const response = await fetch('/cleanup/run', {
        method: 'POST'
      });
      const result = await response.json();
      
      if (result.success) {
        alert(`Cleanup completed. Deleted ${result.data.totalDeleted} records.`);
        await loadSystemData();
      } else {
        alert(`Cleanup failed: ${result.message}`);
      }
    } catch (error) {
      alert('Network error during cleanup');
    } finally {
      actionLoading = '';
    }
  }

  function openConfirmModal(action: any) {
    confirmAction = action;
    showConfirmModal = true;
  }

  async function executeAction() {
    showConfirmModal = false;
    if (confirmAction) {
      await confirmAction.fn();
      confirmAction = null;
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString('ru-RU');
  }
</script>

<svelte:head>
  <title>Система - Admin Panel</title>
</svelte:head>

<div class="p-6 space-y-6">
  <!-- Page Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Управление системой</h1>
      <p class="text-gray-600 mt-1">Резервное копирование, очистка данных и настройки</p>
    </div>
    <Button variant="outline" size="sm" on:click={loadSystemData}>
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      Обновить
    </Button>
  </div>

  {#if loading}
    <div class="flex justify-center items-center py-12">
      <Spinner size="lg" />
    </div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Backup Management -->
      <Card variant="shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Резервное копирование</h2>
            <Badge variant="secondary">
              {backupStatus?.status?.totalBackups || 0} бэкапов
            </Badge>
          </div>
        </div>

        <div class="p-6 space-y-6">
          <!-- Backup Status -->
          {#if backupStatus?.status?.lastBackup}
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
              <div class="flex items-center">
                <svg class="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p class="text-sm font-medium text-green-800">Последний бэкап</p>
                  <p class="text-sm text-green-700">
                    {backupStatus.status.lastBackup.fileName} - {formatDate(backupStatus.status.lastBackup.createdAt)}
                  </p>
                  <p class="text-xs text-green-600">
                    Размер: {formatBytes(backupStatus.status.lastBackup.fileSize)}
                  </p>
                </div>
              </div>
            </div>
          {:else}
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div class="flex items-center">
                <svg class="w-5 h-5 text-yellow-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L4.35 15.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <p class="text-sm text-yellow-800">Бэкапы не найдены</p>
              </div>
            </div>
          {/if}

          <!-- Backup Actions -->
          <div class="space-y-3">
            <h3 class="text-sm font-medium text-gray-700">Создать бэкап</h3>
            <div class="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                size="sm"
                on:click={() => createBackup('full')}
                loading={actionLoading === 'backup-full'}
                disabled={actionLoading !== ''}
              >
                {#if actionLoading === 'backup-full'}
                  <Spinner size="sm" className="mr-2" />
                {/if}
                Полный
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                on:click={() => createBackup('schema')}
                loading={actionLoading === 'backup-schema'}
                disabled={actionLoading !== ''}
              >
                {#if actionLoading === 'backup-schema'}
                  <Spinner size="sm" className="mr-2" />
                {/if}
                Только схема
              </Button>
            </div>
          </div>

          <!-- Recent Backups -->
          {#if backupStatus?.backups && backupStatus.backups.length > 0}
            <div class="space-y-2">
              <h3 class="text-sm font-medium text-gray-700">Последние бэкапы</h3>
              <div class="max-h-40 overflow-y-auto space-y-1">
                {#each backupStatus.backups.slice(0, 5) as backup}
                  <div class="flex justify-between items-center p-2 bg-gray-50 rounded text-sm">
                    <div>
                      <p class="font-medium text-gray-900">{backup.fileName}</p>
                      <p class="text-gray-500 text-xs">
                        {formatDate(backup.createdAt)} • {formatBytes(backup.fileSize)}
                      </p>
                    </div>
                    <Badge variant="secondary">{backup.type}</Badge>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </Card>

      <!-- Data Cleanup -->
      <Card variant="shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Очистка данных</h2>
        </div>

        <div class="p-6 space-y-6">
          <!-- Cleanup Statistics -->
          {#if cleanupStats?.recordsToDelete}
            <div class="space-y-3">
              <h3 class="text-sm font-medium text-gray-700">Данные к удалению</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Токены верификации:</span>
                  <span class="font-medium">{cleanupStats.recordsToDelete.verificationTokens}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">SMS логи:</span>
                  <span class="font-medium">{cleanupStats.recordsToDelete.smsLogs}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Email логи:</span>
                  <span class="font-medium">{cleanupStats.recordsToDelete.emailLogs}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Rate limit записи:</span>
                  <span class="font-medium">{cleanupStats.recordsToDelete.rateLimitEntries}</span>
                </div>
              </div>
              
              <div class="pt-2 border-t border-gray-200">
                <div class="flex justify-between font-medium">
                  <span class="text-gray-900">Всего записей:</span>
                  <span class="text-gray-900">{cleanupStats.recordsToDelete.total}</span>
                </div>
              </div>
            </div>
          {/if}

          <!-- Cleanup Actions -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-sm font-medium text-gray-700">Автоматическая очистка</h3>
                <p class="text-xs text-gray-500">Удаление устаревших данных по расписанию</p>
              </div>
              <Badge variant="success">Активна</Badge>
            </div>

            <Button
              variant="outline"
              size="sm"
              on:click={() => openConfirmModal({
                title: 'Запустить очистку данных',
                message: 'Это действие удалит устаревшие записи. Продолжить?',
                fn: runCleanup
              })}
              loading={actionLoading === 'cleanup'}
              disabled={actionLoading !== '' || !cleanupStats?.recordsToDelete?.total}
            >
              {#if actionLoading === 'cleanup'}
                <Spinner size="sm" className="mr-2" />
              {/if}
              Запустить очистку
            </Button>
          </div>

          <!-- Retention Policy -->
          {#if cleanupStats?.retentionConfig}
            <div class="space-y-2">
              <h3 class="text-sm font-medium text-gray-700">Политика хранения</h3>
              <div class="bg-gray-50 rounded-lg p-3 space-y-1 text-xs">
                <div class="flex justify-between">
                  <span class="text-gray-600">Токены верификации:</span>
                  <span class="text-gray-900">7-30 дней</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">SMS/Email логи:</span>
                  <span class="text-gray-900">90 дней</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Rate limit записи:</span>
                  <span class="text-gray-900">1 день</span>
                </div>
              </div>
            </div>
          {/if}
        </div>
      </Card>
    </div>

    <!-- System Settings -->
    <Card variant="shadow">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Настройки системы</h2>
      </div>

      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Maintenance Mode -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-medium text-gray-700">Режим обслуживания</h3>
              <Badge variant="secondary">Выключен</Badge>
            </div>
            <p class="text-xs text-gray-500">
              Временное отключение системы для обслуживания
            </p>
            <Button variant="outline" size="sm" disabled>
              Включить
            </Button>
          </div>

          <!-- Debug Mode -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-medium text-gray-700">Режим отладки</h3>
              <Badge variant="warning">Включен</Badge>
            </div>
            <p class="text-xs text-gray-500">
              Подробные логи и информация об ошибках
            </p>
            <Button variant="outline" size="sm" disabled>
              Выключить
            </Button>
          </div>

          <!-- Cache Management -->
          <div class="space-y-2">
            <h3 class="text-sm font-medium text-gray-700">Управление кэшем</h3>
            <p class="text-xs text-gray-500">
              Очистка кэша приложения и данных
            </p>
            <Button variant="outline" size="sm" disabled>
              Очистить кэш
            </Button>
          </div>
        </div>
      </div>
    </Card>
  {/if}
</div>

<!-- Confirmation Modal -->
<Modal 
  bind:open={showConfirmModal} 
  title={confirmAction?.title || 'Подтверждение'}
  size="sm"
>
  <div class="text-center">
    <div class="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
      <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L4.35 15.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    </div>
    <p class="text-gray-600">{confirmAction?.message || 'Вы уверены?'}</p>
  </div>

  <svelte:fragment slot="footer" let:close>
    <div class="flex justify-end space-x-3">
      <Button variant="outline" on:click={close}>
        Отмена
      </Button>
      <Button variant="primary" on:click={executeAction}>
        Подтвердить
      </Button>
    </div>
  </svelte:fragment>
</Modal>