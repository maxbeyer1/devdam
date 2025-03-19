// api_cdn.js
//
// Endpoints for CDN URLs
//
const photoapp_db = require("./photoapp_db.js");
const { query_database, getContentType } = require("./utility.js");

//
// GET /asset/:assetid/cdn-urls - Get CDN URLs for all variants of an asset
//
exports.get_cdn_urls = async (req, res) => {
  console.log("**Call to get /asset/:assetid/cdn-urls...");

  try {
    let assetid = req.params.assetid;

    if (isNaN(assetid)) {
      res.status(400).json({
        message: "Invalid asset ID format",
        data: null,
      });
      return;
    }

    // Get asset details
    let assetSql = `
      SELECT assetname
      FROM assets
      WHERE assetid = ${assetid};
    `;

    let assetResult = await query_database(photoapp_db, assetSql);

    if (assetResult.length === 0) {
      res.status(404).json({
        message: "Asset not found",
        data: null,
      });
      return;
    }

    let assetname = assetResult[0].assetname;

    // Get variants
    let variantSql = `
      SELECT variantid, variant_type, width, height, format, quality, cdn_url
      FROM asset_variants
      WHERE assetid = ${assetid}
      ORDER BY width ASC;
    `;

    let variants = await query_database(photoapp_db, variantSql);

    if (variants.length === 0) {
      res.status(404).json({
        message: "No variants found for this asset",
        data: null,
      });
      return;
    }

    // Group variants by type
    let variantsByType = {};
    variants.forEach((variant) => {
      if (!variantsByType[variant.variant_type]) {
        variantsByType[variant.variant_type] = [];
      }
      variantsByType[variant.variant_type].push(variant);
    });

    // Generate HTML snippets
    let imgTag = generateImgTag(variants, assetname);
    let pictureTag = generatePictureTag(variantsByType, assetname);

    // Format response
    let response = {
      asset_id: assetid,
      asset_name: assetname,
      variants: variants,
      html_snippets: {
        img_tag: imgTag,
        picture_tag: pictureTag,
      },
    };

    res.json({
      message: "success",
      data: response,
    });
  } catch (err) {
    console.log("**Error in /asset/:assetid/cdn-urls");
    console.log(err.message);

    res.status(500).json({
      message: err.message,
      data: null,
    });
  }
};

// Generate an <img> tag with srcset for responsive images
function generateImgTag(variants, assetname) {
  // Filter out variants suitable for srcset (same format, different sizes)
  // For simplicity, using all webp variants if available, otherwise any variants
  let webpVariants = variants.filter((v) => v.format === "webp");
  let srcsetVariants = webpVariants.length > 0 ? webpVariants : variants;

  // If no variants, return empty string
  if (srcsetVariants.length === 0) return "";

  // Generate srcset attribute
  let srcset = srcsetVariants.map((v) => `${v.cdn_url} ${v.width}w`).join(", ");

  // Use the smallest variant as fallback src
  let smallestVariant = srcsetVariants.reduce((prev, curr) =>
    prev.width < curr.width ? prev : curr
  );

  // Generate sizes attribute (simplified example)
  let sizes = "(max-width: 600px) 100vw, (max-width: 1200px) 50vw, 33vw";

  return `<img src="${smallestVariant.cdn_url}" srcset="${srcset}" sizes="${sizes}" alt="${assetname}" />`;
}

// Generate a <picture> element with different format options
function generatePictureTag(variantsByType, assetname) {
  let formatVariants = {};

  let formats = new Set();
  for (let type in variantsByType) {
    variantsByType[type].forEach((variant) => {
      formats.add(variant.format);
    });
  }

  // For each format find the variant with best quality
  formats.forEach((format) => {
    let bestVariant = null;
    for (let type in variantsByType) {
      variantsByType[type].forEach((variant) => {
        if (variant.format === format) {
          if (!bestVariant || variant.width > bestVariant.width) {
            bestVariant = variant;
          }
        }
      });
    }
    if (bestVariant) {
      formatVariants[format] = bestVariant;
    }
  });

  let picture = "<picture>\n";

  // Add source elements for each format (webp first if available)
  const formatPriority = ["webp", "avif", "jpg", "jpeg", "png"];

  let sortedFormats = [...formats].sort((a, b) => {
    const indexA = formatPriority.indexOf(a);
    const indexB = formatPriority.indexOf(b);
    return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
  });

  // Add source elements for each format
  sortedFormats.forEach((format) => {
    if (formatVariants[format]) {
      const variant = formatVariants[format];
      const mimeType = getContentType("." + format);
      picture += `  <source srcset="${variant.cdn_url}" type="${mimeType}" />\n`;
    }
  });

  // Add fallback img tag (using the last format as fallback)
  if (sortedFormats.length > 0) {
    const fallbackFormat = sortedFormats[sortedFormats.length - 1];
    const fallbackVariant = formatVariants[fallbackFormat];
    picture += `  <img src="${fallbackVariant.cdn_url}" alt="${assetname}" />\n`;
  }

  picture += "</picture>";
  return picture;
}
