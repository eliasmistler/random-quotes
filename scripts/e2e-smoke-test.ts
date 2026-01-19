import { test, expect, BrowserContext, Page } from '@playwright/test';
import * as readline from 'readline';

/**
 * E2E Smoke Test for Random Quotes
 *
 * Simulates a complete 2-player game from start to finish.
 * - Host creates game and gets invite code
 * - Guest joins using invite code
 * - Host starts the game
 * - Both players submit answers each round
 * - Judge picks a winner
 * - Game continues until someone reaches 5 points
 * - Verifies game over screen shows
 *
 * Interactive mode (--interactive):
 * - Press Ctrl-C to pause the test
 * - Press Enter to resume
 */

interface Player {
  context: BrowserContext;
  page: Page;
  name: string;
  isHost: boolean;
}

// Interactive mode state
const isInteractive = process.env.INTERACTIVE === 'true';
let isPaused = false;
let pauseResolver: (() => void) | null = null;
let readlineInterface: readline.Interface | null = null;

/**
 * Set up interactive mode signal handler
 */
function setupInteractiveMode(): void {
  if (!isInteractive) return;

  // Handle Ctrl-C to pause instead of exit
  process.on('SIGINT', () => {
    if (isPaused) {
      // Already paused, ignore
      return;
    }
    isPaused = true;
    console.log('\n\n========================================');
    console.log('TEST PAUSED - Inspect the browser now');
    console.log('Press Enter to resume...');
    console.log('========================================\n');
  });

  // Set up readline to listen for Enter key
  readlineInterface = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  readlineInterface.on('line', () => {
    if (isPaused && pauseResolver) {
      console.log('Resuming test...\n');
      isPaused = false;
      const resolver = pauseResolver;
      pauseResolver = null;
      resolver();
    }
  });

  // Handle close event to clean up
  readlineInterface.on('close', () => {
    readlineInterface = null;
  });
}

/**
 * Clean up interactive mode resources
 */
function cleanupInteractiveMode(): void {
  if (readlineInterface) {
    readlineInterface.close();
    readlineInterface = null;
  }
}

/**
 * Check if paused and wait for resume in interactive mode
 */
async function checkPause(): Promise<void> {
  if (!isInteractive || !isPaused) return;

  return new Promise<void>((resolve) => {
    pauseResolver = resolve;
  });
}

// Initialize interactive mode
setupInteractiveMode();

test.describe('Random Quotes - Full Game Smoke Test', () => {
  let host: Player;
  let guest: Player;
  let inviteCode: string;

  test.beforeAll(async ({ browser }) => {
    // Create two separate browser contexts for two players
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();

    host = {
      context: hostContext,
      page: await hostContext.newPage(),
      name: 'TestHost',
      isHost: true,
    };

    guest = {
      context: guestContext,
      page: await guestContext.newPage(),
      name: 'TestGuest',
      isHost: false,
    };
  });

  test.afterAll(async () => {
    await host.context.close();
    await guest.context.close();
    cleanupInteractiveMode();
  });

  test('Complete game from lobby to game over', async () => {
    if (isInteractive) {
      console.log('\n========================================');
      console.log('INTERACTIVE MODE ENABLED');
      console.log('Press Ctrl-C at any time to pause');
      console.log('========================================\n');
    }

    // ============================================
    // PHASE 1: Host creates game
    // ============================================
    console.log('Phase 1: Host creating game...');
    await checkPause();

    await host.page.goto('/');
    await host.page.waitForLoadState('networkidle');

    // Enter nickname
    await host.page.fill('#nickname', host.name);

    // Click "Start New Game" button
    await host.page.click('.create-btn');

    // Wait for lobby and get invite code
    await host.page.waitForURL(/\/lobby|\/game/);
    await expect(host.page.locator('.invite-section h2')).toBeVisible({ timeout: 10000 });

    // Get the invite code from the page - it's displayed in .invite-code-display with individual .code-letter spans
    const inviteCodeElement = host.page.locator('.invite-code-display');
    await expect(inviteCodeElement).toBeVisible();
    inviteCode = (await inviteCodeElement.textContent()) || '';
    inviteCode = inviteCode.replace(/[^A-Z0-9]/gi, ''); // Clean up any extra characters
    console.log(`Invite code: ${inviteCode}`);
    expect(inviteCode).toHaveLength(6);

    // ============================================
    // PHASE 2: Guest joins game
    // ============================================
    console.log(`Phase 2: Guest joining game with code: ${inviteCode}`);
    await checkPause();

    await guest.page.goto('/');
    await guest.page.waitForLoadState('networkidle');

    // Wait for the form to be ready
    await expect(guest.page.locator('#nickname')).toBeVisible({ timeout: 5000 });

    // Enter nickname
    await guest.page.fill('#nickname', guest.name);
    console.log('Guest entered nickname');

    // Enter invite code
    await guest.page.fill('.invite-input', inviteCode);
    console.log('Guest entered invite code');

    // Wait for join button to be enabled
    await guest.page.waitForTimeout(300);

    // Click join button
    await guest.page.click('.join-btn');
    console.log('Guest clicked join');

    // Wait for lobby
    await guest.page.waitForURL(/\/lobby/, { timeout: 15000 });
    console.log('Guest arrived at lobby');

    // Verify both players see each other in lobby
    await expect(host.page.locator(`text=${guest.name}`)).toBeVisible({ timeout: 15000 });
    await expect(guest.page.locator(`text=${host.name}`)).toBeVisible({ timeout: 15000 });
    console.log('Both players in lobby');

    // ============================================
    // PHASE 3: Host starts the game
    // ============================================
    console.log('Phase 3: Host starting game...');
    await checkPause();

    // Host clicks start game button
    await host.page.click('.start-btn');

    // Wait for game to start - both players should see the game view with tiles
    await expect(host.page.locator('.round-info')).toBeVisible({ timeout: 15000 });
    await expect(guest.page.locator('.tiles-grid')).toBeVisible({ timeout: 15000 });
    console.log('Game started - Round 1');

    // ============================================
    // PLAY ROUNDS UNTIL GAME OVER
    // (Default points_to_win is 5)
    // ============================================
    let roundNumber = 1;
    const maxRounds = 10; // Safety limit

    while (roundNumber <= maxRounds) {
      // Check if game is already over
      const gameOver = await host.page.locator('.game-over').isVisible().catch(() => false);
      if (gameOver) {
        console.log(`Game over detected after Round ${roundNumber - 1}`);
        break;
      }

      await playRound(host, guest, roundNumber);
      roundNumber++;
    }

    // ============================================
    // VERIFY GAME OVER
    // ============================================
    console.log('Verifying game over...');
    await checkPause();

    // Check for game over screen
    await expect(host.page.locator('.game-over')).toBeVisible({ timeout: 15000 });
    await expect(guest.page.locator('.game-over')).toBeVisible({ timeout: 15000 });

    // Verify the final scores are displayed
    await expect(host.page.locator('.final-scores')).toBeVisible();

    console.log('Game completed successfully!');
  });
});

/**
 * Play a single round of the game
 *
 * Game flow:
 * 1. All players submit their answers (both host and guest)
 * 2. After all submissions, a judge is selected
 * 3. Judge picks the winning answer
 * 4. Results are shown
 * 5. Host advances to next round (or game ends)
 */
async function playRound(
  host: Player,
  guest: Player,
  roundNumber: number
): Promise<void> {
  console.log(`\n--- Round ${roundNumber} ---`);
  await checkPause();

  // Both players submit their answers
  await submitAnswer(host);
  await submitAnswer(guest);

  // Wait for judging phase - one player will become the judge
  console.log('Waiting for judging phase...');
  await host.page.waitForTimeout(1000);

  // Find who is the judge by checking which page has the judging area
  const hostIsJudge = await host.page.locator('.judging-area').isVisible().catch(() => false);
  const judge = hostIsJudge ? host : guest;
  console.log(`${judge.name} is the judge`);

  // Judge picks the winner
  await pickWinner(judge);

  // Wait for results phase
  console.log('Waiting for results...');
  await host.page.waitForTimeout(500);

  // Host advances to next round (or game over)
  console.log('Host advancing...');
  await advanceRound(host);

  // Check if game is over or continue to next round
  const gameOver = await host.page.locator('.game-over').isVisible().catch(() => false);
  if (!gameOver) {
    // Wait for next round to start - tiles grid should be visible
    await expect(host.page.locator('.tiles-grid')).toBeVisible({ timeout: 10000 });
    console.log(`Advanced to Round ${roundNumber + 1}`);
  }
}

/**
 * Submit an answer by selecting tiles
 */
async function submitAnswer(player: Player): Promise<void> {
  await checkPause();
  console.log(`${player.name} submitting answer...`);

  // Wait for tiles to be visible
  await expect(player.page.locator('.tiles-grid .tile').first()).toBeVisible({ timeout: 10000 });

  // Select first 2-3 available tiles
  const tiles = player.page.locator('.tiles-grid .tile:not(.selected)');
  const tileCount = await tiles.count();
  const tilesToSelect = Math.min(3, tileCount);

  for (let i = 0; i < tilesToSelect; i++) {
    await tiles.nth(i).click();
    await player.page.waitForTimeout(200); // Small delay between clicks
  }

  // Click submit button
  await player.page.click('.submit-btn');

  console.log(`${player.name} submitted`);
}

/**
 * Judge picks a winner from submissions
 */
async function pickWinner(judge: Player): Promise<void> {
  await checkPause();
  // Wait for judging phase - look for judging area
  await expect(judge.page.locator('.judging-area')).toBeVisible({ timeout: 15000 });

  // Look for submission cards to click
  const submissionCards = judge.page.locator('.judging-area .submission-card');

  // Wait for cards to be visible
  await expect(submissionCards.first()).toBeVisible({ timeout: 10000 });

  // Click the first submission card (in 2-player game, there's only one)
  await submissionCards.first().click();

  // Wait for results phase OR game over (game skips results when ending)
  await expect(
    judge.page.locator('.results-area, .game-over').first()
  ).toBeVisible({ timeout: 10000 });
  console.log('Winner selected');
}

/**
 * Host advances to the next round
 */
async function advanceRound(host: Player): Promise<void> {
  await checkPause();
  // Check if game is already over (no advance button when game ends)
  const gameOver = await host.page.locator('.game-over').isVisible().catch(() => false);
  if (gameOver) {
    console.log('Game over - no advance needed');
    return;
  }

  // Look for the advance/next round button
  const advanceButton = host.page.locator('button:has-text("Next Round"), button:has-text("Advance"), button.advance-btn');

  await expect(advanceButton).toBeVisible({ timeout: 15000 });
  await advanceButton.click();

  // Wait for the transition
  await host.page.waitForTimeout(500);
}
