<?cs include "header.cs" ?>
<?cs include "macros.cs" ?>

<div id="content" class="irclogs">
 <div class="wrapper">
  <h1>IRC Logs</h1>
  <h2><?cs var:day ?>. <?cs var:month ?> <?cs var:year ?></h2>
  <table class="minical">
   <?cs include "irclogs_cal.cs" ?>
  </table>
  <table class="irclog">
  <?cs each:line = lines ?>
   <?cs if:line.mode == 'action' ?>
    <tr class="action">
     <td class="time">[<a href="#T<?cs var:line.time ?>" id="T<?cs var:line.time ?>"><?cs var:line.time ?></a>]</td>
     <td class="left">*</td>
     <td class="right"><?cs var:line.nickname ?> <?cs var:line.text ?></td>
    </tr>
   <?cs /if ?><?cs if:line.mode == 'channel' ?>
    <tr class="channel">
     <td class="time">[<a href="#T<?cs var:line.time ?>" id="T<?cs var:line.time ?>"><?cs var:line.time ?></a>]</td>
     <td class="left">&lt;<span class="<?cs var:line.class ?>"><?cs var:line.nickname ?></span>&gt;</td>
     <td class="right"><?cs var:line.text ?></td>
    </tr>
   <?cs /if ?><?cs if:line.mode == 'server' ?>
    <tr class="server">
     <td class="time">[<a href="#T<?cs var:line.time ?>" id="T<?cs var:line.time ?>"><?cs var:line.time ?></a>]</td> 
     <td class="left">***</td>
     <td class="right"><?cs var:line.nickname ?> <?cs var:line.text ?></td>
    </tr>
   <?cs /if ?>
  <?cs /each ?>
  </table>
 </div>
</div>

<?cs include "footer.cs" ?>
