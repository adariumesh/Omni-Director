# FIBO Portfolio Templates

This directory contains HTML templates for generating professional portfolios with the FIBO Export Engine.

## Available Templates

### Professional (`professional.html`)
- **Style**: Clean, business-oriented design
- **Features**: 
  - Structured layout with clear sections
  - Statistics cards and metrics
  - Professional typography
  - Comprehensive metadata display
  - About section with technical specifications
- **Best For**: Corporate presentations, client deliveries, formal showcases

### Creative (`creative.html`)
- **Style**: Artistic, visually rich design
- **Features**:
  - Hero section with call-to-action
  - Masonry gallery layout
  - Creative process visualization
  - Artistic typography (Playfair Display + Inter)
  - Parallax effects and smooth animations
- **Best For**: Art portfolios, creative showcases, visual storytelling

### Minimal (`minimal.html`)
- **Style**: Clean, typography-focused design
- **Features**:
  - Minimal interface with maximum focus on content
  - Monospace typography (IBM Plex)
  - Simple grid layouts
  - Technical details in colophon
  - No visual distractions
- **Best For**: Technical documentation, clean presentations, focus on the work

## Template Variables

Templates use double-brace syntax for variable replacement:

### Core Variables
- `{{portfolio_title}}` - Portfolio name/title
- `{{portfolio_subtitle}}` - Subtitle or tagline
- `{{portfolio_description}}` - Main description
- `{{asset_count}}` - Number of assets
- `{{creation_date}}` - Portfolio creation date
- `{{generation_timestamp}}` - Full generation timestamp

### Branding Variables
- `{{logo_html}}` - Logo image HTML (if provided)
- `{{footer_text}}` - Footer text
- `{{custom_css}}` - Custom CSS styles
- `{{analytics_code}}` - Analytics tracking code

### Layout Variables
- `{{layout_class}}` - CSS class for layout style (grid, masonry, etc.)
- `{{portfolio_theme}}` - Theme identifier
- `{{layout_style}}` - Layout style identifier

### Content Variables
- `{{asset_cards}}` - Generated HTML for asset cards
- `{{search_controls}}` - Search interface HTML
- `{{filter_controls}}` - Filter controls HTML
- `{{lightbox_html}}` - Lightbox modal HTML
- `{{custom_nav_items}}` - Additional navigation items

## Creating Custom Templates

1. **Create Template File**: Add a new `.html` file in this directory
2. **Use Variables**: Include template variables where dynamic content should appear
3. **Include Required Elements**:
   - Asset card container with class matching layout
   - CSS and JS file references
   - Lightbox modal (if enabled)
4. **Test Template**: Use the template name in portfolio configuration

### Template Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{portfolio_title}}</title>
    <link rel="stylesheet" href="css/style.css">
    {{custom_css}}
</head>
<body class="theme-{{portfolio_theme}}">
    <!-- Header -->
    <header>
        <h1>{{portfolio_title}}</h1>
        <p>{{portfolio_description}}</p>
    </header>
    
    <!-- Gallery -->
    <main>
        <div class="portfolio-gallery {{layout_class}}">
            {{asset_cards}}
        </div>
    </main>
    
    <!-- Lightbox -->
    {{lightbox_html}}
    
    <!-- Scripts -->
    <script src="js/script.js"></script>
</body>
</html>
```

## CSS Classes

Templates should include these CSS classes for proper functionality:

### Gallery Classes
- `.portfolio-gallery` - Main gallery container
- `.layout-grid` - Grid layout
- `.layout-masonry` - Masonry layout
- `.layout-list` - List layout

### Asset Classes
- `.asset-card` - Individual asset container
- `.asset-image` - Image container
- `.asset-info` - Asset metadata container
- `.asset-title` - Asset title
- `.asset-description` - Asset description

### Interactive Classes
- `.hidden` - Hidden state for filtering
- `.lightbox` - Lightbox modal
- `.view-btn` - View/open buttons

## Template Guidelines

1. **Responsive Design**: All templates should work on mobile devices
2. **Semantic HTML**: Use proper HTML5 semantic elements
3. **Accessibility**: Include proper ARIA labels and alt text
4. **Performance**: Optimize for fast loading
5. **SEO**: Include proper meta tags and structured data
6. **Cross-browser**: Test in multiple browsers

## Customization

Templates can be customized by:

1. **CSS Overrides**: Use the `custom_css` variable
2. **Theme Classes**: Apply theme-specific styles via body classes
3. **Layout Modifications**: Adjust the gallery container structure
4. **Color Schemes**: Use CSS custom properties for theming

## Example Usage

```python
from orchestrator.agents.portfolio_generator import PortfolioConfig

config = PortfolioConfig(
    name="My Portfolio",
    template="professional",  # Use professional.html
    theme=PortfolioTheme.PROFESSIONAL,
    layout=LayoutStyle.GRID
)
```

The portfolio generator will automatically load and process the template with the provided variables.