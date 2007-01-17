<?cs include "header.cs" ?>
<?cs include "macros.cs" ?>

<div id="content" class="irclogs">
 <div class="wrapper">
  <h1>IRC Logs</h1>
  <table class="minical">
   <?cs include "irclogs_cal.cs" ?>
  </table>
  <?cs if:viewmode == 'years' ?>
   <ul class="years">
   <?cs each:year = years ?>
    <li><a href="<?cs var:year.href ?>"><?cs var:year.caption ?></a></li>
   <?cs /each ?>
   </ul>
  <?cs /if ?>
  <?cs if:viewmode == 'months' ?>
   <ul class="months">
   <?cs each:month = months ?>
    <li><a href="<?cs var:month.href ?>"><?cs var:month.caption ?> <?cs var:year ?></a></li>
   <?cs /each ?>
   </ul>
  <?cs /if ?>
  <?cs if:viewmode == 'days' ?>
   <ul class="days">
   <?cs each:day = days ?>
    <li><a href="<?cs var:day.href ?>"><?cs var:day.caption ?>. <?cs var:month ?> <?cs var:year ?></a></li>
   <?cs /each ?>
   </ul>
  <?cs /if ?>
 </div>
</div>

<?cs include "footer.cs" ?>
