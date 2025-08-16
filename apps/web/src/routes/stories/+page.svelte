<script lang="ts">
  import { onMount } from 'svelte';
  import { storiesStore, storiesActions } from '$lib/stores/stories';
  import { formatDate } from '$lib/utils/date';
  import Button from '$lib/components/ui/Button.svelte';
  import Card from '$lib/components/ui/Card.svelte';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  let currentPage = 1;
  let limit = 12;

  $: if ($page.url.searchParams.has('page')) {
    currentPage = parseInt($page.url.searchParams.get('page') || '1');
  }

  onMount(() => {
    storiesActions.loadStories(currentPage, limit);
  });

  function handlePageChange(newPage: number) {
    currentPage = newPage;
    const url = new URL($page.url);
    url.searchParams.set('page', newPage.toString());
    goto(url.toString());
    storiesActions.loadStories(newPage, limit);
  }

  function handleStoryClick(link: string) {
    goto(`/stories/${link}`);
  }

  function getThumbnailUrl(thumbnail: string | null | undefined) {
    if (!thumbnail) return '/images/story-default.jpg';
    return thumbnail.startsWith('http') ? thumbnail : `/uploads/${thumbnail}`;
  }

  function truncateExcerpt(excerpt: string | null, maxLength: number = 150) {
    if (!excerpt) return '';
    return excerpt.length > maxLength ? excerpt.substring(0, maxLength) + '...' : excerpt;
  }
</script>

<svelte:head>
  <title>Истории - YuYu Lolita</title>
  <meta name="description" content="Читайте интересные истории о японской моде и культуре лолита от YuYu Lolita" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-pink-50 to-purple-50">
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Истории <span class="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600">YuYu Lolita</span>
      </h1>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto">
        Окунитесь в мир японской моды и культуры через наши увлекательные истории
      </p>
    </div>

    <!-- Loading state -->
    {#if $storiesStore.loading}
      <div class="flex justify-center items-center py-12">
        <Spinner size="large" />
      </div>
    {:else if $storiesStore.error}
      <!-- Error state -->
      <div class="text-center py-12">
        <div class="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <div class="text-red-600 mb-4">
            <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-red-800 mb-2">Ошибка загрузки</h3>
          <p class="text-red-600 mb-4">{$storiesStore.error}</p>
          <Button 
            variant="secondary" 
            on:click={() => storiesActions.loadStories(currentPage, limit)}
          >
            Попробовать снова
          </Button>
        </div>
      </div>
    {:else if $storiesStore.stories.length === 0}
      <!-- Empty state -->
      <div class="text-center py-12">
        <div class="text-gray-400 mb-4">
          <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <h3 class="text-xl font-medium text-gray-900 mb-2">Пока нет историй</h3>
        <p class="text-gray-600">Скоро здесь появятся интересные истории!</p>
      </div>
    {:else}
      <!-- Stories grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
        {#each $storiesStore.stories as story}
          <Card className="group cursor-pointer transform hover:scale-105 transition-all duration-300 hover:shadow-xl" variant="shadow" padding="none">
            <div 
              class="h-full flex flex-col"
              on:click={() => handleStoryClick(story.link)}
              on:keydown={(e) => e.key === 'Enter' && handleStoryClick(story.link)}
              role="button"
              tabindex="0"
            >
              <!-- Thumbnail -->
              <div class="relative h-48 bg-gradient-to-br from-pink-100 to-purple-100 rounded-t-lg overflow-hidden">
                <img 
                  src={getThumbnailUrl(story.thumbnail)} 
                  alt={story.title}
                  class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                  loading="lazy"
                />
                <div class="absolute inset-0 bg-black/10 group-hover:bg-black/20 transition-colors duration-300"></div>
              </div>
              
              <!-- Content -->
              <div class="flex-1 p-6">
                <div class="flex items-center justify-between mb-3">
                  <div class="text-sm text-gray-500">
                    {formatDate(story.publishedAt || story.createdAt)}
                  </div>
                  {#if story.author}
                    <div class="text-sm text-pink-600 font-medium">
                      {story.author.name}
                    </div>
                  {/if}
                </div>
                
                <h3 class="text-xl font-semibold text-gray-900 mb-3 group-hover:text-pink-600 transition-colors duration-300">
                  {story.title}
                </h3>
                
                {#if story.excerpt}
                  <p class="text-gray-600 leading-relaxed mb-4">
                    {truncateExcerpt(story.excerpt)}
                  </p>
                {/if}
                
                <div class="flex items-center text-pink-600 font-medium">
                  <span class="mr-2">Читать далее</span>
                  <svg class="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </div>
          </Card>
        {/each}
      </div>

      <!-- Pagination -->
      {#if $storiesStore.pagination && $storiesStore.pagination.totalPages > 1}
        <div class="flex justify-center items-center space-x-2">
          <Button 
            variant="outline" 
            size="sm"
            disabled={!$storiesStore.pagination.hasPrev}
            on:click={() => handlePageChange(currentPage - 1)}
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            Назад
          </Button>
          
          {#each Array.from({length: $storiesStore.pagination.totalPages}, (_, i) => i + 1) as pageNum}
            {#if pageNum === currentPage}
              <Button variant="primary" size="sm" disabled>
                {pageNum}
              </Button>
            {:else if Math.abs(pageNum - currentPage) <= 2 || pageNum === 1 || pageNum === $storiesStore.pagination.totalPages}
              <Button 
                variant="outline" 
                size="sm"
                on:click={() => handlePageChange(pageNum)}
              >
                {pageNum}
              </Button>
            {:else if Math.abs(pageNum - currentPage) === 3}
              <span class="px-2 text-gray-500">...</span>
            {/if}
          {/each}
          
          <Button 
            variant="outline" 
            size="sm"
            disabled={!$storiesStore.pagination.hasNext}
            on:click={() => handlePageChange(currentPage + 1)}
          >
            Вперед
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </Button>
        </div>
      {/if}
    {/if}
  </div>
</div>