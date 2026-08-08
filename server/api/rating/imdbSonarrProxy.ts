import ExternalAPI from '@server/api/externalapi';
import { type IMDBRating } from '@server/api/rating/imdbRadarrProxy';
import cacheManager from '@server/lib/cache';

interface SkyhookRating {
  count: number;
  value: string;
}

interface SkyhookShow {
  title: string;
  imdbId?: string;
  rating?: SkyhookRating;
}

/**
 * This is a best-effort API, mirroring IMDBRadarrProxy but for series.
 *
 * Sonarr hosts a public metadata proxy (Skyhook) that's in use by all
 * Sonarr instances, and it carries an IMDb-sourced rating per series.
 * There is no first-party equivalent of the Radarr IMDB proxy for TV,
 * so this uses Skyhook's own rating field instead.
 */
class IMDBSonarrProxy extends ExternalAPI {
  constructor() {
    super(
      'https://skyhook.sonarr.tv/v1',
      {},
      {
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        nodeCache: cacheManager.getCache('imdb').data,
      }
    );
  }

  /**
   * Ask Sonarr's Skyhook service for a series' rating
   *
   * @param tvdbId TheTVDB id of the series
   */
  public async getSeriesRatings(tvdbId: number): Promise<IMDBRating | null> {
    try {
      const data = await this.get<SkyhookShow>(`/tvdb/shows/en/${tvdbId}`);

      if (!data?.rating?.value || !data.imdbId) {
        return null;
      }

      return {
        title: data.title,
        url: `https://www.imdb.com/title/${data.imdbId}`,
        criticsScore: Number(data.rating.value),
        criticsScoreCount: data.rating.count,
      };
    } catch (e) {
      throw new Error(
        `[IMDB SONARR PROXY API] Failed to retrieve series ratings: ${e.message}`,
        { cause: e }
      );
    }
  }
}

export default IMDBSonarrProxy;
